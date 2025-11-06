{{ config(materialized='table', schema='main') }}

with source_data as (

    select *
    from read_parquet('data/yellow_tripdata_2025-09.parquet')
)


select *
from source_data