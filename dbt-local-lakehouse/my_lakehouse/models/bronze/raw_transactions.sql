{{ config(materialized='view') }}

SELECT *
FROM read_csv_auto('../data/bronze/raw_transactions.csv')