with source as (
    {#-
    Normally we would select from the table here, but we are using seeds to load
    our data in this project
    #}
    SELECT * FROM {{ ref('raw_orders') }}
),

renamed as (
    SELECT
        id AS order_id,
        user_id as customer_id,
        order_date,
        status
    FROM source
)

select * from renamed