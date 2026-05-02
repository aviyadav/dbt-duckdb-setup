# Local ETL Pipeline — dbt + DuckDB

A fully local, end-to-end ELT pipeline for coffee shop analytics.  
Raw data is **generated** with Faker, **loaded** into DuckDB, and **transformed** by dbt into mart-level models for revenue performance and budget variance reporting — no external database or cloud service required.

---

## Tech Stack

| Tool | Version | Role |
|---|---|---|
| [Python](https://python.org) | 3.13 | Runtime & scripting |
| [uv](https://github.com/astral-sh/uv) | latest | Package & venv manager |
| [Faker](https://faker.readthedocs.io/) | 40.15.0 | Synthetic data generation |
| [PyArrow](https://arrow.apache.org/docs/python/) | 24.0.0 | Typed in-process data transport (IPC) |
| [Polars](https://pola.rs/) | 1.40.1 | DataFrame ops & CSV writing |
| [DuckDB](https://duckdb.org/) | 1.5.2 | Embedded OLAP database |
| [dbt-core](https://docs.getdbt.com/) | 1.11.8 | SQL transformation layer |
| [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | 1.10.1 | DuckDB adapter for dbt |

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│  EXTRACT & GENERATE                                     │
│                                                         │
│  generate_data.py                                       │
│  ├── Faker + multiprocessing (chunked, memory-safe)     │
│  ├── PyArrow IPC  ──►  Polars write_csv                 │
│  ├── data/sales_data.csv   (100,000 rows)               │
│  └── data/budget_data.csv  (720 rows)                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  LOAD                                                   │
│                                                         │
│  load.py                                                │
│  ├── read_csv_auto('data/sales_data.csv')               │
│  ├── read_csv_auto('data/budget_data.csv')              │
│  └── coffeeshop.duckdb                                  │
│       ├── raw.source_sales   (100,000 rows)             │
│       └── raw.source_budget  (720 rows)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  TRANSFORM  (dbt · coffee_analytics project)            │
│                                                         │
│  Staging layer                                          │
│  ├── stg_sales    ── casts, renames, computes revenue   │
│  └── stg_budget   ── extracts month & year from date    │
│                                                         │
│  Marts layer                                            │
│  ├── sales_performance  ── store × month aggregation    │
│  └── finance_variance   ── actual vs budget + variance  │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
local-etl-pipeline-dbt-duckdb/
│
├── data/
│   ├── sales_data.csv          ← 100 000 sales transactions
│   └── budget_data.csv         ← 720 monthly budget rows (20 stores × 3 yrs)
│
├── coffee_analytics/           ← dbt project root
│   ├── models/
│   │   ├── sources.yml         ← declares raw.source_sales & raw.source_budget
│   │   ├── staging/
│   │   │   ├── stg_sales.sql
│   │   │   └── stg_budget.sql
│   │   └── marts/
│   │       ├── sales_performance.sql
│   │       └── finance_variance.sql
│   ├── profiles.yml            ← DuckDB connection (points at coffeeshop.duckdb)
│   ├── dbt_project.yml
│   └── quick_check.py         ← ad-hoc DuckDB query script
│
├── generate_data.py            ← Step 1 — synthetic data generation
├── load.py                     ← Step 2 — CSV → DuckDB raw schema
├── main.py                     ← Pipeline entry point
├── pyproject.toml
├── .python-version             ← pins Python 3.13
└── README.md
```

---

## Quick Start

```
# 1. Install dependencies
uv sync

# 2. Generate CSV seed files
uv run python generate_data.py

# 3. Load CSVs into DuckDB
uv run python load.py

# 4. Run dbt transformations
cd coffee_analytics
uv run dbt build

# 5. (Optional) Quick sanity query
uv run python quick_check.py
```

---

## Step-by-Step Guide

### Step 1 — Generate Data (`generate_data.py`)

Generates two CSV files inside `data/` using a chunked multiprocessing pipeline.

**How it works:**

- The workload is split into chunks of 5,000 rows each, distributed across all available CPU cores via `multiprocessing.Pool`.
- Each worker process generates data with **Faker**, builds a typed **PyArrow `RecordBatch`**, and returns it to the main process serialised as **PyArrow IPC bytes** (avoids pickle overhead).
- The main process deserialises each batch, converts it to a **Polars `DataFrame`**, and appends it to the CSV file — only one chunk lives in memory at a time.

| File | Rows | Columns |
|---|---|---|
| `data/sales_data.csv` | 100,000 | `order_id`, `store_id`, `transaction_date`, `product_name`, `quantity`, `unit_price` |
| `data/budget_data.csv` | 720 | `store_id`, `date`, `target_revenue`, `regional_manager_name`, `is_promotional_month` |

**Sales data details:**
- 20 stores (`STORE_001` → `STORE_020`)
- 20 products (Laptop, Monitor, Keyboard, …)
- Date range: 2022-01-01 → 2024-12-31
- Quantity: 1–50 units · Unit price: $5.00–$500.00

**Budget data details:**
- One row per store per month across 3 years (2022–2024)
- Each store has one consistent regional manager
- Promotional months (January, July, November, December) carry a ×1.20 revenue uplift
- `is_promotional_month` is `T` or `F`

---

### Step 2 — Load Data (`load.py`)

Reads both CSVs into a persistent **DuckDB** file (`coffeeshop.duckdb`) under the `raw` schema using DuckDB's built-in `read_csv_auto`, which infers column types automatically.

```
raw.source_sales   ← data/sales_data.csv
raw.source_budget  ← data/budget_data.csv
```

Run from the project root (so relative paths resolve correctly):

```
uv run python load.py
```

Expected output:

```
🚀 Starting ELT Process...
... Loading Sales Data
... Loading Budget Data
✅ Loaded 100000 sales records.
✅ Loaded 720 budget records
```

---

### Step 3 — Transform with dbt (`coffee_analytics/`)

The `coffee_analytics` dbt project connects to `coffeeshop.duckdb` and builds four models in two layers.

#### Model DAG

```
source_sales  ──►  stg_sales  ──►  sales_performance  ──►┐
                                                          ├──►  finance_variance
source_budget  ──►  stg_budget  ──────────────────────────┘
```

All models materialise as **views** by default.

---

#### Sources (`models/sources.yml`)

Declares the two raw tables under the source name `bean_raw` (schema `raw`).

---

#### Staging Layer

##### `stg_sales`
Reads from `raw.source_sales`. Casts `transaction_date` to `DATE`, renames `product_name` to `product`, and derives `total_revenue = quantity × unit_price`.

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR | Unique order UUID |
| `store_id` | VARCHAR | Store identifier |
| `transaction_date` | DATE | Date of transaction |
| `product` | VARCHAR | Product name |
| `quantity` | BIGINT | Units sold |
| `unit_price` | DOUBLE | Price per unit |
| `total_revenue` | DOUBLE | `quantity × unit_price` |

##### `stg_budget`
Reads from `raw.source_budget`. Unpacks the `date` column into `month` and `year` integers for downstream joining.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `month` | BIGINT | Budget month (1–12) |
| `year` | BIGINT | Budget year |
| `target_revenue` | DOUBLE | Monthly revenue target |
| `regional_manager_name` | VARCHAR | Regional manager |
| `is_promotional_month` | VARCHAR | `T` or `F` |

---

#### Marts Layer

##### `sales_performance`
Aggregates `stg_sales` to a **store × month** grain using `date_trunc`.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `sales_month` | TIMESTAMP | Month (truncated to the 1st) |
| `total_items_sold` | HUGEINT | Total units sold that month |
| `gross_revenue` | DOUBLE | Total revenue that month |

##### `finance_variance`
Joins `sales_performance` (actuals) to `stg_budget` (targets) on `store_id` + month, producing a revenue variance report.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `sales_month` | TIMESTAMP | Reporting month |
| `actual_revenue` | DOUBLE | Gross revenue (from `sales_performance`) |
| `target_revenue` | DOUBLE | Budget target (from `stg_budget`) |
| `revenue_variance` | DOUBLE | `actual − target` |
| `achievement_pct` | DOUBLE | `(actual ÷ target) × 100`, rounded to 2 dp |

---

#### Running dbt

```
cd coffee_analytics

# Check the connection
uv run dbt debug

# Build all models
uv run dbt build

# Run individual layers
uv run dbt run --select staging           # staging models only
uv run dbt run --select marts             # mart models only
uv run dbt run --select finance_variance  # single model
```

---

### Step 4 — Query Results (`quick_check.py`)

A lightweight ad-hoc script that connects directly to `coffeeshop.duckdb` and queries `finance_variance`:

```
cd coffee_analytics
uv run python quick_check.py
```

---

## Configuration

### `coffee_analytics/profiles.yml`
Configures dbt's connection to DuckDB. Points at the local `coffeeshop.duckdb` file with 2 threads.

```
coffee_analytics:
    outputs:
        dev:
            type: duckdb
            path: <absolute-path-to>/coffee_analytics/coffeeshop.duckdb
            threads: 2
    target: dev
```

> **Note:** The `path` in `profiles.yml` uses an absolute path. If you move or clone the project, update this to match your local path.

### `coffee_analytics/dbt_project.yml`
Standard dbt project config. Models are discovered automatically from `models/`. Default materialisation is `view`.

---

## Python Version Note

`dbt-duckdb` (and its `mashumaro` dependency) is **not compatible with Python 3.14**. The project is pinned to **Python 3.13** via `.python-version`. This is enforced automatically when using `uv`.
