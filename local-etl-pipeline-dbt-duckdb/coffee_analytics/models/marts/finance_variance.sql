with actuals as (
    select * from {{ ref('sales_performance') }}
),

budgets as (
    select * from {{ ref('stg_budget') }}
)

select
    a.store_id,
    a.sales_month,
    a.gross_revenue as actual_revenue,
    b.target_revenue,
    -- Calculate variance
    (a.gross_revenue - b.target_revenue) as revenue_variance,
    round((a.gross_revenue / b.target_revenue) * 100, 2) as achievement_pct
from actuals a
left join budgets b
    on a.store_id = b.store_id
    and month(a.sales_month) = b.month
