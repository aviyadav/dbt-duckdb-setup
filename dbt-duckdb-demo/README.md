Welcome to your new dbt project!

### Using the starter project

Try running the following commands:
- dbt run
- dbt test


### Resources:
- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)
- Check out [Discourse](https://discourse.getdbt.com/) for commonly asked questions and answers
- Join the [chat](https://community.getdbt.com/) on Slack for live discussions and support
- Find [dbt events](https://events.getdbt.com) near you
- Check out [the blog](https://blog.getdbt.com/) for the latest news on dbt's development and best practices
- https://medium.com/@chinmayeeudupa/wait-you-can-run-dbt-locally-without-a-warehouse-in-just-a-minute-9af6797769d2


#### Duckdb

```
cd dbt_project
duckdb dev.duckdb


CALL start_ui();

┌────────────────────────────────────────────┐
│                   result                   │
│                  varchar                   │
├────────────────────────────────────────────┤
│ Navigate browser to http://localhost:4213/ │
└────────────────────────────────────────────┘

SELECT * FROM marts.marts_orders LIMIT 10;

```



#### all commands

```
mkdir dbt_duckdb_demo && cd dbt_duckdb_demo
python3 -m venv .venv && source .venv/bin/activate

pip install dbt-duckdb duckdb

dbt init dbt_project

cd dbt_project
dbt debug

mkdir -p models/staging
mkdir -p models/marts

-- create packages.yml

dbt deps


dbt compile

dbt seed

dbt run -s tag:staging
dbt run -s tag:marts

dbt docs generate
dbt docs serve

pip install dbt-colibri

colibri generate


output in dist folder


```