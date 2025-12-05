with source as (
    {#-
    Normally we would select from the table here, but we are using seeds to load
    our data in this project
    #}
    SELECT * FROM {{ ref('raw_customers') }}
),

renamed as (
    SELECT
        id AS customer_id,
        first_name,
        last_name
    FROM source
)


select * from renamed