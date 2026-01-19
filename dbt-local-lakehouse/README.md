# Local Lakehouse using dbt and DuckDB

A local data lakehouse implementation using dbt-core with DuckDB adapter. This project demonstrates a medallion architecture (bronze → silver → gold) for data processing entirely on your local machine.

## Project Structure

```
local-lakehouse/
├── data/                          # Data lake storage
│   ├── bronze/                    # Raw data layer
│   │   ├── raw_transactions.csv
│   │   └── raw_transactions.parquet
│   ├── silver/                    # Cleaned/staged data
│   │   └── stg_transactions.parquet
│   └── gold/                      # Aggregated business data
│       └── category_summary.parquet
├── my_lakehouse/                  # dbt project
│   ├── models/
│   │   ├── bronze/               # Raw data ingestion
│   │   ├── silver/               # Data transformation
│   │   └── gold/                 # Business aggregations
│   └── dbt_project.yml
├── generate_data_pd.py            # Data generator (pandas + PyArrow)
├── generate_data_pl.py            # Data generator (polars)
└── pyproject.toml
```

## Prerequisites

- Python 3.13+
- uv (recommended) or pip

## Setup

1. **Create and activate virtual environment:**
   ```bash
   uv venv
   .venv\Scripts\Activate.ps1   # Windows PowerShell
   source .venv/bin/activate     # Linux/macOS
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   # or
   pip install -e .
   ```

3. **Set the required environment variable:**

   **Windows PowerShell:**
   ```powershell
   $env:DBT_PROJECT_DIR = "c:\Users\uname\codebase\local-lakehouse\my_lakehouse"
   ```

   **Linux/macOS:**
   ```bash
   export DBT_PROJECT_DIR=/path/to/local-lakehouse/my_lakehouse
   ```

## Usage

### 1. Generate Sample Data

Generate 5 million rows of dummy transaction data using multiprocessing and PyArrow for optimal performance:

```bash
python generate_data_pd.py
```

Or using Polars:
```bash
python generate_data_pl.py
```

### 2. Run dbt Build

Navigate to the dbt project and run the build:

```bash
cd my_lakehouse
dbt build
```

This will:
- Create a view for `raw_transactions` (bronze layer)
- Transform and filter data to `stg_transactions.parquet` (silver layer)
- Aggregate revenue by category to `category_summary.parquet` (gold layer)

### 3. Verify Output

Check that all files were created:
```powershell
Get-ChildItem -Recurse data | Select-Object FullName
```

## Data Pipeline

| Layer  | Model               | Materialization | Output                              |
|--------|---------------------|-----------------|-------------------------------------|
| Bronze | raw_transactions    | view            | DuckDB view (reads CSV)             |
| Silver | stg_transactions    | external        | `data/silver/stg_transactions.parquet` |
| Gold   | revenue_by_category | external        | `data/gold/category_summary.parquet`   |

## Dependencies

- **dbt-core** - Data transformation framework
- **dbt-duckdb** - DuckDB adapter for dbt
- **duckdb** - Embedded analytical database
- **pandas** - Data manipulation (with PyArrow backend)
- **polars** - High-performance DataFrame library
- **pyarrow** - Columnar data format and fast I/O