WITH staging_data as (
    SELECT
        *
    FROM {{ ref('original_headline') }}
)
SELECT
    CASE
        WHEN headline = 'Data engineer' THEN 'Junior data engineer'
        ELSE headline
    END AS job_title,
    description__text AS description
FROM
    staging_data