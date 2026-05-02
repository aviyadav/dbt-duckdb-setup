#!/usr/bin/env python3
"""
generate_data.py
================
Generates two CSV seed files inside the ``data/`` directory:

  data/sales_data.csv   – 100 000 sales transaction rows
  data/budget_data.csv  – 3 years × 12 months per store (monthly budget rows)

Design decisions
----------------
* **Faker** supplies realistic random values (UUIDs, names, …).
* **Multiprocessing** distributes chunk generation across all CPU cores.
* **Chunked writing** keeps peak memory usage proportional to chunk size,
  not to the full dataset.
* **PyArrow IPC** is the transport layer between worker processes and the
  main process (zero-copy, strongly typed, and pickle-free).
* **Polars** is used for the final CSV serialisation step in the main process.
"""

from __future__ import annotations

import multiprocessing as mp
import random
import time
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.ipc as pa_ipc
from faker import Faker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR: Path = Path(__file__).parent / "data"

# Sales
TOTAL_SALES_RECORDS: int = 100_000
SALES_CHUNK_SIZE: int = 5_000  # rows per worker task  → ~20 tasks for 100 k

# Stores / budget
NUM_STORES: int = 20
BUDGET_YEARS: int = 3
BUDGET_YEAR_START: int = 2022

PRODUCTS: list[str] = [
    "Laptop",
    "Monitor",
    "Keyboard",
    "Mouse",
    "Headphones",
    "Webcam",
    "Desk Chair",
    "Standing Desk",
    "USB Hub",
    "External SSD",
    "Printer",
    "Scanner",
    "Tablet",
    "Smartphone",
    "Smart Watch",
    "Wireless Charger",
    "Desk Lamp",
    "Cable Manager",
    "Notebook",
    "Pen Set",
]

STORE_IDS: list[str] = [f"STORE_{i:03d}" for i in range(1, NUM_STORES + 1)]

SALES_DATE_START: date = date(2022, 1, 1)
SALES_DATE_END: date = date(2024, 12, 31)

# Months treated as promotional (November, December, July, January)
PROMOTIONAL_MONTHS: frozenset[int] = frozenset({1, 7, 11, 12})

# ---------------------------------------------------------------------------
# PyArrow IPC helpers  (serialise/deserialise a RecordBatch to raw bytes so
# multiprocessing can ship it through its pipe without pickle overhead)
# ---------------------------------------------------------------------------


def _batch_to_bytes(batch: pa.RecordBatch) -> bytes:
    sink = pa.BufferOutputStream()
    with pa_ipc.new_stream(sink, batch.schema) as writer:
        writer.write_batch(batch)
    return sink.getvalue().to_pybytes()


def _bytes_to_batch(data: bytes) -> pa.RecordBatch:
    reader = pa_ipc.open_stream(data)
    return reader.read_next_batch()


# ---------------------------------------------------------------------------
# Helper: write a Polars DataFrame to CSV, appending if the file already
# exists (skips header on append).
# ---------------------------------------------------------------------------


def _write_or_append(df: pl.DataFrame, path: Path, first: bool) -> None:
    if first:
        df.write_csv(str(path))  # creates file with header
    else:
        csv_text: str = df.write_csv(include_header=False)
        with open(path, "ab") as fh:  # binary append avoids platform newline
            fh.write(csv_text.encode("utf-8"))


# ===========================================================================
# SALES DATA
# ===========================================================================

# ---------------------------------------------------------------------------
# Worker — runs inside a child process
# ---------------------------------------------------------------------------


def _sales_worker(args: tuple) -> bytes:
    """
    Generate *n_records* sales rows using Faker + stdlib random.

    Each worker seeds its own Faker / random state from *chunk_id* so
    results are deterministic yet unique across chunks.

    Returns the chunk as a PyArrow RecordBatch encoded in IPC stream format.
    """
    chunk_id, n_records, store_ids, products, date_start, date_end = args

    fake = Faker()
    Faker.seed(chunk_id)
    rng = random.Random(chunk_id)

    date_range_days = (date_end - date_start).days

    order_ids = [fake.uuid4() for _ in range(n_records)]
    store_col = [rng.choice(store_ids) for _ in range(n_records)]
    txn_dates = [
        (date_start + timedelta(days=rng.randint(0, date_range_days))).isoformat()
        for _ in range(n_records)
    ]
    product_col = [rng.choice(products) for _ in range(n_records)]
    quantity_col = [rng.randint(1, 50) for _ in range(n_records)]
    unit_price_col = [round(rng.uniform(5.0, 500.0), 2) for _ in range(n_records)]

    schema = pa.schema(
        [
            pa.field("order_id", pa.string()),
            pa.field("store_id", pa.string()),
            pa.field("transaction_date", pa.string()),
            pa.field("product_name", pa.string()),
            pa.field("quantity", pa.int32()),
            pa.field("unit_price", pa.float64()),
        ]
    )

    batch = pa.record_batch(
        [order_ids, store_col, txn_dates, product_col, quantity_col, unit_price_col],
        schema=schema,
    )
    return _batch_to_bytes(batch)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def generate_sales_data(output_path: Path) -> None:
    n_full, remainder = divmod(TOTAL_SALES_RECORDS, SALES_CHUNK_SIZE)
    chunk_sizes = [SALES_CHUNK_SIZE] * n_full + ([remainder] if remainder else [])

    tasks = [
        (idx, sz, STORE_IDS, PRODUCTS, SALES_DATE_START, SALES_DATE_END)
        for idx, sz in enumerate(chunk_sizes)
    ]

    n_workers = min(mp.cpu_count(), len(tasks))
    print(
        f"  Workers : {n_workers}  |  Chunks : {len(tasks)}  "
        f"|  Chunk size : {SALES_CHUNK_SIZE:,}"
    )

    first = True
    with mp.Pool(processes=n_workers) as pool:
        # imap keeps only one result in memory at a time → memory-safe
        for raw in pool.imap(_sales_worker, tasks, chunksize=1):
            arrow_batch: pa.RecordBatch = _bytes_to_batch(raw)
            df: pl.DataFrame = pl.from_arrow(arrow_batch)  # PyArrow → Polars
            _write_or_append(df, output_path, first)
            first = False

    print(f"  Written : {output_path}  ({TOTAL_SALES_RECORDS:,} rows)")


# ===========================================================================
# BUDGET DATA
# ===========================================================================

# ---------------------------------------------------------------------------
# Worker — runs inside a child process
# ---------------------------------------------------------------------------


def _budget_worker(args: tuple) -> bytes:
    """
    Generate 3 years of monthly budget rows for a single store.

    Returns the chunk as a PyArrow RecordBatch encoded in IPC stream format.
    """
    store_id, manager_name, year_start, num_years, promo_months = args

    rng = random.Random(hash(store_id) & 0xFFFF_FFFF)
    base_target = rng.uniform(50_000, 500_000)

    rows_store: list[str] = []
    rows_date: list[str] = []
    rows_target: list[float] = []
    rows_manager: list[str] = []
    rows_promo: list[str] = []

    for yr_off in range(num_years):
        year = year_start + yr_off
        for month in range(1, 13):
            is_promo = month in promo_months
            seasonal = 1.0 + 0.25 * rng.uniform(-1.0, 1.0)
            promo_factor = 1.20 if is_promo else 1.0
            target = round(base_target * seasonal * promo_factor, 2)

            rows_store.append(store_id)
            rows_date.append(date(year, month, 1).isoformat())
            rows_target.append(target)
            rows_manager.append(manager_name)
            rows_promo.append("T" if is_promo else "F")

    schema = pa.schema(
        [
            pa.field("store_id", pa.string()),
            pa.field("date", pa.string()),
            pa.field("target_revenue", pa.float64()),
            pa.field("regional_manager_name", pa.string()),
            pa.field("is_promotional_month", pa.string()),
        ]
    )

    batch = pa.record_batch(
        [rows_store, rows_date, rows_target, rows_manager, rows_promo],
        schema=schema,
    )
    return _batch_to_bytes(batch)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def generate_budget_data(output_path: Path, managers: list[str]) -> None:
    total_rows = NUM_STORES * BUDGET_YEARS * 12
    tasks = [
        (store_id, managers[idx], BUDGET_YEAR_START, BUDGET_YEARS, PROMOTIONAL_MONTHS)
        for idx, store_id in enumerate(STORE_IDS)
    ]

    n_workers = min(mp.cpu_count(), len(tasks))
    print(
        f"  Workers : {n_workers}  |  Stores : {NUM_STORES}  "
        f"|  Years : {BUDGET_YEARS}  |  Total rows : {total_rows:,}"
    )

    first = True
    with mp.Pool(processes=n_workers) as pool:
        for raw in pool.imap(_budget_worker, tasks, chunksize=1):
            arrow_batch: pa.RecordBatch = _bytes_to_batch(raw)
            df: pl.DataFrame = pl.from_arrow(arrow_batch)  # PyArrow → Polars
            _write_or_append(df, output_path, first)
            first = False

    print(f"  Written : {output_path}  ({total_rows:,} rows)")


# ===========================================================================
# Entry point
# ===========================================================================


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-generate one manager name per store in the main process so the
    # mapping stays consistent regardless of worker scheduling order.
    seed_faker = Faker()
    Faker.seed(42)
    managers: list[str] = [seed_faker.name() for _ in range(NUM_STORES)]

    wall_start = time.perf_counter()

    print("\n[1/2] Generating sales data …")
    t = time.perf_counter()
    generate_sales_data(DATA_DIR / "sales_data.csv")
    print(f"      Done in {time.perf_counter() - t:.2f}s")

    print("\n[2/2] Generating budget data …")
    t = time.perf_counter()
    generate_budget_data(DATA_DIR / "budget_data.csv", managers)
    print(f"      Done in {time.perf_counter() - t:.2f}s")

    print(f"\nTotal wall-clock time : {time.perf_counter() - wall_start:.2f}s")
    print("All files are in the  : data/ folder\n")


if __name__ == "__main__":
    # Required guard for multiprocessing on Windows (spawn start method)
    main()
