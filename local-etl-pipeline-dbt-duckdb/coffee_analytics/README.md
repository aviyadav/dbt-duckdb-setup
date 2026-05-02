# Coffee Analytics — Local ETL Pipeline (dbt + DuckDB)

A local analytics pipeline that transforms raw coffee shop sales and budget data into mart-level models for revenue performance and variance reporting. Built with **dbt** and **DuckDB** — no external data warehouse required.

---

## Stack

| Tool | Version | Role |
|---|---|---|
| [dbt-core](https://docs.getdbt.com/) | 1.11.8 | Transformation layer |
| [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | 1.10.1 | DuckDB adapter for dbt |
| [DuckDB](https://duckdb.org/) | 1.10.1 | Embedded OLAP database |
| Python | 3.x | Runtime / virtual environment |

---

## Project Structure

```coffee_analytics/dbt_project.yml#L1-1
```

```/dev/null/tree.txt#L1-20
coffee_analytics/
├── models/
│   ├── sources.yml              # Source definitions (raw schema)
│   ├── staging/
│   │   ├── stg_sales.sql        # Cleans & casts raw sales data
│   │   └── stg_budget.sql       # Extracts month/year from budget dates
│   └── marts/
│       ├── sales_performance.sql # Monthly revenue aggregated by store
│       └── finance_variance.sql  # Actual vs budget with variance %
├── seeds/
├── tests/
├── macros/
├── profiles.yml                 # DuckDB connection config
├── dbt_project.yml
└── coffeeshop.duckdb            # Local DuckDB database file
```

---

## Data Sources

Both source tables live in the `raw` schema of `coffeeshop.duckdb` and are registered in `models/sources.yml` under the source name `bean_raw`.

### `raw.source_sales`
100,000 individual order transactions across 20 stores and 3 years (2022–2024).

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR | Unique order identifier (UUID) |
| `store_id` | VARCHAR | Store identifier (e.g. `STORE_001`) |
| `transaction_date` | DATE | Date of the transaction |
| `product_name` | VARCHAR | Product sold (20 distinct products) |
| `quantity` | BIGINT | Units sold in the order |
| `unit_price` | DOUBLE | Price per unit |

**Coverage:** 20 stores · 20 products · 2022-01-01 → 2024-12-31

### `raw.source_budget`
720 monthly budget targets — one row per store per month (20 stores × 36 months).

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `date` | DATE | First day of the budget month |
| `target_revenue` | DOUBLE | Monthly revenue target |
| `regional_manager_name` | VARCHAR | Manager responsible for the store |
| `is_promotional_month` | BOOLEAN | Whether a promotion ran that month |

---

## Models

### DAG

```/dev/null/dag.txt#L1-8
source_sales  ──►  stg_sales  ──►  sales_performance  ──►  finance_variance
                                                                  ▲
source_budget  ──►  stg_budget  ──────────────────────────────────┘
```

All models are materialised as **views** (default).

---

### Staging

#### `stg_sales`
Selects from `raw.source_sales`, casts `transaction_date` to `DATE`, renames `product_name` to `product`, and computes `total_revenue = quantity * unit_price`.

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR | Unique order identifier |
| `store_id` | VARCHAR | Store identifier |
| `transaction_date` | DATE | Transaction date |
| `product` | VARCHAR | Product name |
| `quantity` | BIGINT | Units sold |
| `unit_price` | DOUBLE | Price per unit |
| `total_revenue` | DOUBLE | `quantity × unit_price` |

#### `stg_budget`
Selects from `raw.source_budget` and unpacks the budget date into separate `month` and `year` integers for easier joining downstream.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `month` | BIGINT | Budget month (1–12) |
| `year` | BIGINT | Budget year |
| `target_revenue` | DOUBLE | Monthly revenue target |
| `regional_manager_name` | VARCHAR | Regional manager |
| `is_promotional_month` | BOOLEAN | Promotional month flag |

---

### Marts

#### `sales_performance`
Aggregates `stg_sales` to a **store × month** grain.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `sales_month` | TIMESTAMP | Month truncated to the 1st (via `date_trunc`) |
| `total_items_sold` | HUGEINT | Total units sold that month |
| `gross_revenue` | DOUBLE | Total revenue that month |

#### `finance_variance`
Joins `sales_performance` (actuals) to `stg_budget` (targets) on `store_id` and month, producing a revenue variance report.

| Column | Type | Description |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `sales_month` | TIMESTAMP | Reporting month |
| `actual_revenue` | DOUBLE | Gross revenue from `sales_performance` |
| `target_revenue` | DOUBLE | Budget target from `stg_budget` |
| `revenue_variance` | DOUBLE | `actual − target` |
| `achievement_pct` | DOUBLE | `(actual / target) × 100`, rounded to 2 dp |

---

## Setup & Usage

### Prerequisites
- Python 3.x
- A virtual environment with `dbt-duckdb` installed

### 1. Activate the virtual environment

```/dev/null/shell.sh#L1-2
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 2. Verify the connection

```/dev/null/shell.sh#L1-1
dbt debug
```

### 3. Run all models

```/dev/null/shell.sh#L1-1
dbt build
```

### 4. Run individual layers

```/dev/null/shell.sh#L1-4
dbt run --select staging          # staging models only
dbt run --select marts            # mart models only
dbt run --select finance_variance # single model
```

---

## Configuration

### `profiles.yml`
Configures the DuckDB connection. The database file path must point to `coffee_analytics/coffeeshop.duckdb` (the file that contains the `raw` schema).

```coffee_analytics/profiles.yml#L1-8
coffee_analytics:
    outputs:
        dev:
            type: duckdb
            path: /home/avinash/codebase/python-base/local-etl-pipeline-dbt-duckdb/coffee_analytics/coffeeshop.duckdb
            threads: 2

    target: dev
```

### `dbt_project.yml`
The project uses the default dbt layout. Models are discovered automatically from the `models/` directory.
