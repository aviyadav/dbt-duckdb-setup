import duckdb

con = duckdb.connect("coffeeshop.duckdb")
# Querying the dbt model (which is now a table/view in the DB)
df = con.sql("SELECT * FROM finance_variance WHERE achievement_pct < 300").df()
print(df)
