{{ config(materialized='table', schema='main') }}

with source_data as (

    select *
    from read_csv('data/life-expectancy-data.csv')
)


select *
from source_data