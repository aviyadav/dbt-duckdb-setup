select
    store_id,
    date_part('month', date) as month,
    date_part('year', date) as year,
    target_revenue,
    regional_manager_name,
    is_promotional_month -- (T/F)
from {{ source('bean_raw', 'source_budget') }}
