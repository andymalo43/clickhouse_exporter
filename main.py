import os
import time
import typer
import tomllib
import polars as pl
import clickhouse_connect
from pathlib import Path
from multiprocessing import Pool, Manager
from tqdm import tqdm

app = typer.Typer(help="Parallel orchestrator for ClickHouse exports with progress bar")

EXCEL_MAX_ROWS_XLSX = 1_048_576
EXCEL_MAX_ROWS_XLS = 65_536


# ----------- Utils ----------- #
def load_config(config_file: str) -> dict:
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    env_map = {
        "CLICKHOUSE_HOST": ("clickhouse", "host"),
        "CLICKHOUSE_PORT": ("clickhouse", "port"),
        "CLICKHOUSE_USER": ("clickhouse", "username"),
        "CLICKHOUSE_PASSWORD": ("clickhouse", "password"),
        "CLICKHOUSE_DATABASE": ("clickhouse", "database"),
    }

    for env_var, (section, key) in env_map.items():
        if env_var in os.environ:
            config[section][key] = os.environ[env_var]

    return config


def ensure_relative_dir(path: Path):
    if not path.is_absolute():
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        raise ValueError("Seuls les chemins relatifs sont autorisés pour les exports")


def export_data(df: pl.DataFrame, fmt: str, output_path: str):
    path = Path(output_path)
    ensure_relative_dir(path)

    fmt = fmt.lower()
    if fmt == "json":
        path = path.with_suffix(".json")
        df.write_json(path, row_oriented=True)
    elif fmt == "parquet":
        path = path.with_suffix(".parquet")
        df.write_parquet(path)
    elif fmt == "csv":
        path = path.with_suffix(".csv")
        df.write_csv(path)
    elif fmt == "xlsx":
        if df.height > EXCEL_MAX_ROWS_XLSX:
            typer.secho(
                f"⚠️ {df.height:,} lignes dépassent la limite XLSX ({EXCEL_MAX_ROWS_XLSX:,}). Export en Parquet.",
                fg=typer.colors.YELLOW,
            )
            path = path.with_suffix(".parquet")
            df.write_parquet(path)
        else:
            path = path.with_suffix(".xlsx")
            df.to_pandas().to_excel(path, index=False)
    elif fmt == "xls":
        if df.height > EXCEL_MAX_ROWS_XLS:
            typer.secho(
                f"⚠️ {df.height:,} lignes dépassent la limite XLS ({EXCEL_MAX_ROWS_XLS:,}). "
                "Export en XLSX ou Parquet.",
                fg=typer.colors.YELLOW,
            )
            if df.height <= EXCEL_MAX_ROWS_XLSX:
                path = path.with_suffix(".xlsx")
                df.to_pandas().to_excel(path, index=False)
            else:
                path = path.with_suffix(".parquet")
                df.write_parquet(path)
        else:
            path = path.with_suffix(".xls")
            df.to_pandas().to_excel(path, index=False, engine="xlwt")
    else:
        raise ValueError(f"Format non supporté : {fmt}")

    return str(path)


def run_export(args):
    export_def, config, queue = args
    name = export_def.get("name", "unnamed_export")
    query = export_def["query"]
    fmt = export_def["format"]
    output_path = export_def["output_path"]

    start = time.time()
    try:
        client = clickhouse_connect.get_client(
            host=config["clickhouse"]["host"],
            port=int(config["clickhouse"]["port"]),
            username=config["clickhouse"]["username"],
            password=config["clickhouse"]["password"],
            database=config["clickhouse"]["database"],
        )

        result = client.query_arrow(query)
        df = pl.from_arrow(result)
        path = export_data(df, fmt, output_path)
        duration = time.time() - start

        queue.put({
            "name": name,
            "status": "success",
            "rows": df.height,
            "path": path,
            "time": round(duration, 2),
        })
    except Exception as e:
        duration = time.time() - start
        queue.put({
            "name": name,
            "status": "error",
            "error": str(e),
            "time": round(duration, 2),
        })


# ----------- Commandes CLI ----------- #
@app.command()
def export_all(config_file: str, workers: int = typer.Option(4, help="Nombre de processus parallèles")):
    manager = Manager()
    queue = manager.Queue()

    config = load_config(config_file)
    exports = config.get("exports", [])
    if not exports:
        typer.secho("❌ Aucun export défini dans le fichier de config", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"🚀 Lancement de {len(exports)} exports en parallèle avec {workers} workers\n")
    pool_args = [(exp, config, queue) for exp in exports]

    with Pool(processes=workers) as pool:
        res = pool.map_async(run_export, pool_args)

        for _ in tqdm(range(len(exports)), desc="Exports", ncols=100):
            while not queue.empty():
                item = queue.get()
                if item["status"] == "success":
                    typer.secho(
                        f"✅ {item['name']} : {item['rows']:,} lignes exportées en {item['time']}s -> {item['path']}",
                        fg=typer.colors.GREEN,
                    )
                else:
                    typer.secho(
                        f"❌ {item['name']} : erreur en {item['time']}s -> {item['error']}",
                        fg=typer.colors.RED,
                    )
            time.sleep(0.1)

        res.wait()

    typer.echo("\n📊 Tous les exports sont terminés.")


@app.command()
def export_one(config_file: str, export_name: str):
    config = load_config(config_file)
    exports = config.get("exports", [])
    match = next((e for e in exports if e.get("name") == export_name), None)

    if not match:
        typer.secho(f"❌ Aucun export trouvé avec le nom '{export_name}'", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"\n🚀 [{export_name}] Exécution de la requête : {match['query']}")
    run_export((match, config, Manager().Queue()))


if __name__ == "__main__":
    app()
