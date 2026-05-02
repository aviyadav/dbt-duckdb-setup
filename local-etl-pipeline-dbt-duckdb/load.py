import duckdb


def load_data():
    # Connect to a persistent DuckDB file
    # If the file doesn't exist, this creates it
    conn = duckdb.connect("coffeeshop.duckdb")

    print("🚀 Starting ELT Process...")

    # 1. create a schema for raw data
    conn.sql("CREATE SCHEMA IF NOT EXISTS raw;")

    # 2. Load Sales Data (CSV)
    # read_csv_auto is a DuckDB magic function that infers types
    print("... Loading Sales Data")
    conn.sql("""
        CREATE OR REPLACE TABLE raw.source_sales AS
        SELECT * FROM read_csv_auto('data/sales_data.csv');
    """)

    # 3. Load Budget Data (CSV/Excel converted to CSV for simplicity)
    print("... Loading Budget Data")
    conn.sql("""
        CREATE OR REPLACE TABLE raw.source_budget AS
        SELECT * FROM read_csv_auto('data/budget_data.csv');
    """)

    # Validation check - to see if data is loaded into database successfully
    count = conn.sql("SELECT COUNT(*) FROM raw.source_sales").fetchone() or (0,)
    print(f"✅ Loaded {count[0]} sales records.")
    count = conn.sql("SELECT COUNT(*) FROM raw.source_budget").fetchone() or (0,)
    print(f"✅ Loaded {count[0]} budget records")

    conn.close()


if __name__ == "__main__":
    load_data()
