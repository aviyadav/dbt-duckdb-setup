with source as (
    {#-
    Normally we would select from the table here, but we are using seeds to load
    our data in this project
    #}
    SELECT * FROM {{ ref('raw_payments') }}
),
renamed as (
    SELECT
        id AS payment_id,
        order_id,
        payment_method,
        amount / 100 as amount,
    FROM source
)

select * from renamed