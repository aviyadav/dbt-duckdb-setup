select
    order_id,
    store_id,
    transaction_date::DATE as transaction_date,
    product_name as product,
    quantity,
    unit_price,
    (quantity * unit_price) as total_revenue
from {{ source('bean_raw', 'source_sales') }}
