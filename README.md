# My ClickHouse Export CLI

Orchestrator pour exporter des données depuis ClickHouse vers CSV, JSON, Parquet, XLS ou XLSX, avec multiprocessing et suivi en temps réel.

STILL IN DEV

## 📦 Structure du projet

```
my_clickhouse_export/
├─ pyproject.toml
├─ src/
│  └─ my_clickhouse_export/
│      ├─ __init__.py
│      └─ cli.py
└─ config.toml
```

## ⚡ Installation

```bash
# Depuis le dossier racine du projet
pip install -e .
```

Cela installera la CLI `my_clickhouse_export`.

## 📝 Fichier de configuration `config.toml`

```toml
[clickhouse]
host = "localhost"
port = 8123
username = "default"
password = "password"
database = "default"

[[exports]]
name = "users_csv"
query = "SELECT * FROM users LIMIT 1000"
format = "csv"
output_path = "output/users"

[[exports]]
name = "transactions_xlsx"
query = "SELECT * FROM transactions LIMIT 2000000"
format = "xlsx"
output_path = "output/transactions"

[[exports]]
name = "system_numbers_json"
query = "SELECT * FROM system.numbers LIMIT 1000"
format = "json"
output_path = "output/numbers"

[[exports]]
name = "small_data_xls"
query = "SELECT * FROM users LIMIT 50000"
format = "xls"
output_path = "output/users_small"
```

> Les chemins doivent être relatifs.

## 🚀 Utilisation

### Exécuter tous les exports en parallèle

```bash
my_clickhouse_export export-all config.toml
```

Vous pouvez également définir le nombre de processus parallèles :

```bash
my_clickhouse_export export-all config.toml --workers 8
```

### Exécuter un export spécifique

```bash
my_clickhouse_export export-one config.toml users_csv
```

## ⚙️ Fonctionnalités

* Supporte **CSV, JSON, Parquet, XLS, XLSX**
* Multiprocessing avec barre de progression `tqdm`
* Création automatique des dossiers relatifs
* Limites Excel gérées automatiquement avec fallback
* Suivi des exports avec résumé final et logs par export

## 🔧 Dépendances

* Python >= 3.11
* [clickhouse-connect](https://pypi.org/project/clickhouse-connect/)
* [polars](https://pypi.org/project/polars/)
* [typer](https://pypi.org/project/typer/)
* [tqdm](https://pypi.org/project/tqdm/)
* [xlwt](https://pypi.org/project/xlwt/) pour XLS
* [openpyxl](https://pypi.org/project/openpyxl/) pour XLSX

## 📄 Notes

* Si le nombre de lignes dépasse la limite XLS ou XLSX, l'export bascule automatiquement sur XLSX ou Parquet.
* Les erreurs sur un export n'interrompent pas les autres exports.
* Toutes les sorties sont créées dans des chemins relatifs pour éviter tout problème de permissions.

---

### Auteur

Ton Nom - [ton.email@example.com](mailto:ton.email@example.com)
