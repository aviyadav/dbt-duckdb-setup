import polars as pl
import numpy as np
import os
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timedelta


# Constants
TOTAL_ROWS = 5_000_000
CATEGORIES = ['Enterprise', 'SMB', 'Startup', 'Gov']
STATUSES = ['PAID', 'PENDING', 'FAILED']
START_DATE = datetime(2025, 1, 1)
OUTPUT_PATH = 'data_pl/bronze/raw_transactions.csv'


def generate_chunk(args: tuple) -> pl.DataFrame:
    """Generate a chunk of dummy data for a given range of IDs."""
    start_id, end_id, chunk_index = args
    chunk_size = end_id - start_id
    
    # Use a unique random seed per chunk for reproducibility and true randomness
    np.random.seed(start_id)
    
    # Generate timestamps for this chunk
    base_timestamp = START_DATE + timedelta(seconds=5 * start_id)
    timestamps = [base_timestamp + timedelta(seconds=5 * i) for i in range(chunk_size)]
    
    df = pl.DataFrame({
        'id': np.arange(start_id, end_id),
        'category': np.random.choice(CATEGORIES, size=chunk_size),
        'amount': np.random.uniform(10.00, 1000.00, size=chunk_size),
        'status': np.random.choice(STATUSES, size=chunk_size),
        'created_at': timestamps
    })
    
    return df


def generate_dummy_data_parallel() -> pl.DataFrame:
    """Generate dummy data using multiprocessing for parallel chunk generation."""
    print(f"Generating {TOTAL_ROWS:,} rows of dummy data using parallel processing...")
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
        chunk_args.append((start_id, end_id, i))
    
    # Use multiprocessing Pool to generate chunks in parallel
    with Pool(processes=num_processes) as pool:
        chunks = pool.map(generate_chunk, chunk_args)
    
    generation_time = time.time() - start_time
    print(f"Data generation completed in {generation_time:.2f} seconds")
    
    # Combine chunks - Polars concat is very efficient
    print("Combining chunks...")
    combine_start = time.time()
    
    df = pl.concat(chunks)
    
    combine_time = time.time() - combine_start
    print(f"Chunks combined in {combine_time:.2f} seconds")
    
    return df


def save_data(df: pl.DataFrame, filepath: str):
    """Save DataFrame to CSV."""
    print(f"Saving data to {filepath}...")
    save_start = time.time()
    
    # Polars write_csv is already highly optimized
    df.write_csv(filepath)
    
    save_time = time.time() - save_start
    print(f"Data saved in {save_time:.2f} seconds")


def main():
    """Main function to generate and save dummy data using parallel processing."""
    # Create a folder to act as our "S3 Bucket"
    os.makedirs('data_pl/bronze', exist_ok=True)
    
    total_start = time.time()
    
    # Generate data using multiprocessing
    df = generate_dummy_data_parallel()
    
    # Save the combined DataFrame
    save_data(df, OUTPUT_PATH)
    
    total_time = time.time() - total_start
    print(f"\nTotal execution time: {total_time:.2f} seconds")
    print(f"Data generated at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()