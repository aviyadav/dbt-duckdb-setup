WITH staging_data as (
    SELECT * FROM dev.staging.data_field_job_ads
)

SELECT
    headline,
    description__text
FROM
    staging_data