import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.compute as pc
import os
from multiprocessing import Pool, cpu_count
import time


# Constants
TOTAL_ROWS = 5_000_000
CATEGORIES = ['Enterprise', 'SMB', 'Startup', 'Gov']
STATUSES = ['PAID', 'PENDING', 'FAILED']
START_DATE = '2025-01-01'
OUTPUT_PATH = 'data/bronze/raw_transactions.csv'
PARQUET_PATH = 'data/bronze/raw_transactions.parquet'


def generate_chunk_arrow(args: tuple) -> pa.Table:
    """Generate a chunk of dummy data as a PyArrow Table for maximum performance."""
    start_id, end_id, chunk_start_seconds = args
    chunk_size = end_id - start_id
    
    # Use a unique random seed per chunk for reproducibility
    np.random.seed(start_id)
    
    # Generate data using NumPy (fast)
    ids = np.arange(start_id, end_id, dtype=np.int64)
    categories = np.random.choice(CATEGORIES, size=chunk_size)
    amounts = np.random.uniform(10.00, 1000.00, size=chunk_size)
    statuses = np.random.choice(STATUSES, size=chunk_size)
    
    # Generate timestamps as int64 nanoseconds, then convert to PyArrow timestamp
    base_ns = np.datetime64(START_DATE, 'ns').astype(np.int64)
    timestamps_ns = base_ns + (chunk_start_seconds + np.arange(chunk_size) * 5) * 1_000_000_000
    
    # Create PyArrow arrays directly (faster than going through pandas)
    table = pa.table({
        'id': pa.array(ids, type=pa.int64()),
        'category': pa.array(categories, type=pa.string()),
        'amount': pa.array(amounts, type=pa.float64()),
        'status': pa.array(statuses, type=pa.string()),
        'created_at': pa.array(timestamps_ns, type=pa.timestamp('ns'))
    })
    
    return table


def generate_dummy_data_parallel() -> pa.Table:
    """Generate dummy data using multiprocessing with PyArrow Tables."""
    print(f"Generating {TOTAL_ROWS:,} rows of dummy data using parallel processing with PyArrow...")
    start_time = time.time()
    
    # Determine number of processes (use available CPU cores)
    num_processes = cpu_count()
    chunk_size = TOTAL_ROWS // num_processes
    
    print(f"Using {num_processes} processes, {chunk_size:,} rows per chunk")
    
    # Prepare arguments for each chunk
    chunk_args = []
    for i in range(num_processes):
        start_id = i * chunk_size
        end_id = start_id + chunk_size if i < num_processes - 1 else TOTAL_ROWS
        # Calculate the starting seconds offset for this chunk
        chunk_start_seconds = start_id * 5
        chunk_args.append((start_id, end_id, chunk_start_seconds))
    
    # Use multiprocessing Pool to generate chunks in parallel
    with Pool(processes=num_processes) as pool:
        chunks = pool.map(generate_chunk_arrow, chunk_args)
    
    generation_time = time.time() - start_time
    print(f"Data generation completed in {generation_time:.2f} seconds")
    
    # Combine chunks - PyArrow concat_tables is very efficient
    print("Combining chunks...")
    combine_start = time.time()
    
    table = pa.concat_tables(chunks)
    
    combine_time = time.time() - combine_start
    print(f"Chunks combined in {combine_time:.2f} seconds")
    
    return table


def save_data_arrow(table: pa.Table, csv_path: str, parquet_path: str):
    """Save PyArrow Table to both CSV and Parquet formats."""
    
    # Save as CSV using PyArrow's fast CSV writer
    print(f"Saving data to {csv_path}...")
    csv_start = time.time()
    
    pcsv.write_csv(table, csv_path)
    
    csv_time = time.time() - csv_start
    print(f"CSV saved in {csv_time:.2f} seconds")
    
    # Also save as Parquet for even faster future reads
    print(f"Saving data to {parquet_path}...")
    parquet_start = time.time()
    
    import pyarrow.parquet as pq
    pq.write_table(table, parquet_path, compression='snappy')
    
    parquet_time = time.time() - parquet_start
    print(f"Parquet saved in {parquet_time:.2f} seconds")


def generate_dummy_data():
    """Main function to generate and save dummy data using parallel processing with PyArrow."""
    total_start = time.time()
    
    # Generate data using multiprocessing with PyArrow
    table = generate_dummy_data_parallel()
    
    # Save the combined Table
    save_data_arrow(table, OUTPUT_PATH, PARQUET_PATH)
    
    total_time = time.time() - total_start
    print(f"\nTotal execution time: {total_time:.2f} seconds")
    print(f"Data generated at {OUTPUT_PATH} and {PARQUET_PATH}")


if __name__ == "__main__":
    # Create a folder to act as our "S3 Bucket"
    os.makedirs('data/bronze', exist_ok=True)
    generate_dummy_data()
