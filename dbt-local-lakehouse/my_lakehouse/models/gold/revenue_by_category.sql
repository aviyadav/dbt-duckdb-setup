{{ config(
    materialized='external',
    location='../data/gold/category_summary.parquet',
    format='parquet'
) }}

SELECT
    category,
    COUNT(id) AS transaction_count,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_ticket_size
FROM {{ ref('stg_transactions') }}
group by category
order by total_revenue desc