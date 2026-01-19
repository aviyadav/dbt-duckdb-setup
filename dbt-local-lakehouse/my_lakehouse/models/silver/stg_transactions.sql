{{ config(
    materialized='external',
    location='../data/silver/stg_transactions.parquet',
    format='parquet'
) }}

select 
    id,
    category,
    cast(amount as double) as amount,
    status,
    created_at
from {{ ref('raw_transactions') }}
where status = 'PAID'