with sales as (
    select * from {{ ref('stg_sales') }}
)

select
    store_id,
    date_trunc('month', transaction_date) as sales_month,
    sum(quantity) as total_items_sold,
    sum(total_revenue) as gross_revenue
from sales
group by 1, 2
order by 1, 2
