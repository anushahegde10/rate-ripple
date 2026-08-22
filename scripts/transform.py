import pandas as pd
import json
import os
from datetime import datetime

# -------------------------------------------------------
# Configuration — file paths for bronze and silver layers
# Add new sources here without touching the functions below
# -------------------------------------------------------

# input paths — raw bronze files
BRONZE_BOC_POLICY_RATE = "data/bronze/boc_policy_rate_raw.json"
BRONZE_BOC_CPI         = "data/bronze/boc_inflation_cpi_raw.json"
BRONZE_BOC_YIELD_2YR   = "data/bronze/boc_bond_yield_2yr_raw.json"
BRONZE_BOC_YIELD_10YR  = "data/bronze/boc_bond_yield_10yr_raw.json"

# output paths — clean silver files
SILVER_BOC_RATES       = "data/silver/silver_boc_rates.csv"

# StatsCan bronze input paths
BRONZE_STATCAN_HPI          = "data/bronze/statcan_housing_price_index_raw.json"
BRONZE_STATCAN_CONSTRUCTION = "data/bronze/statcan_construction_cost_toronto_raw.json"

# StatsCan silver output paths
SILVER_STATCAN_HOUSING      = "data/silver/silver_statcan_housing.csv"
SILVER_STATCAN_CONSTRUCTION = "data/silver/silver_statcan_construction.csv"

# -------------------------------------------------------
# Table: silver_boc_rates
# Description: Annual average Bank of Canada policy rate,
#              CPI inflation, 2yr and 10yr bond yields.
#              Source: Bank of Canada Valet API
#              Granularity: One row per year (2005 - present)
#              Key column: year (integer, unique, not null)
# -------------------------------------------------------

def transform_boc_series(bronze_path, value_col_name):
    """
    REUSABLE: Cleans any BOC JSON file from bronze.
    - Reads raw JSON observations
    - Extracts date and value
    - Renames cryptic 'v' column to meaningful business name
    - Converts daily data to annual average
    - Adds source and load timestamp
    """
    
    # read raw JSON from bronze — list of daily observations
    with open(bronze_path, "r") as f:
        raw = json.load(f)
    
    # each observation has 'd' for date and a series code key for value
    # we extract just date and value — ignore everything else
    records = []
    for obs in raw:
        date_str = obs["d"]  # date in YYYY-MM-DD format
        
        # value is nested under the series code key — get the first non-date key
        series_key = [k for k in obs.keys() if k != "d"][0]
        value = obs[series_key]["v"]
        
        records.append({"date": date_str, "value": value})
    
    # convert to dataframe
    df = pd.DataFrame(records)
    
    # convert value to numeric — some values may be strings or null markers
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    
    # convert date to datetime so we can extract the year
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    
    # calculate annual average — group all daily values by year
    df_annual = df.groupby("year")["value"].mean().reset_index()
    
    # rename value column to meaningful business name
    df_annual = df_annual.rename(columns={"value": value_col_name})
    
    # round to 4 decimal places — enough precision for rate data
    df_annual[value_col_name] = df_annual[value_col_name].round(4)
    
    # add metadata columns
    df_annual["source"]         = "Bank of Canada Valet API"
    df_annual["load_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_annual


# -------------------------------------------------------
# Table: silver_statcan_housing and silver_statcan_construction
# Description: Annual average Housing Price Index and
#              Building Construction Price Index (Toronto proxy)
#              Source: Statistics Canada WDS API
#              Granularity: One row per year (2005 - present)
#              Key column: year (integer, unique, not null)
#              Note: Raw values are index numbers not percentages
#                    Year over year % change calculated here
# -------------------------------------------------------

def transform_statcan_series(bronze_path, value_col_name, table_description):
    """
    REUSABLE: Cleans any StatsCan JSON file from bronze.
    - Reads nested JSON structure
    - Extracts refPer (date) and value
    - Converts monthly data to annual average
    - Calculates year over year percentage change
    - Adds source and load timestamp
    """

    # read raw JSON from bronze
    with open(bronze_path, "r") as f:
        raw = json.load(f)

    # navigate nested structure to get to data points
    # structure is: response[0]["object"]["vectorDataPoint"]
    data_points = raw[0]["object"]["vectorDataPoint"]

    # extract date and value from each monthly data point
    records = []
    for point in data_points:
        records.append({
            "date": point["refPer"],  # monthly date YYYY-MM-DD
            "value": point["value"]   # raw index value
        })

    # convert to dataframe
    df = pd.DataFrame(records)

    # convert value to numeric — handles any nulls or strings
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # convert date to datetime and extract year
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # calculate annual average of monthly index values
    df_annual = df.groupby("year")["value"].mean().reset_index()

    # rename value column to meaningful business name
    df_annual = df_annual.rename(columns={"value": value_col_name})

    # round to 2 decimal places — index values need less precision
    df_annual[value_col_name] = df_annual[value_col_name].round(2)

    # calculate year over year percentage change
    # this removes base year dependency and makes indexes comparable
    yoy_col_name = value_col_name + "_yoy_pct"
    df_annual[yoy_col_name] = df_annual[value_col_name].pct_change() * 100
    df_annual[yoy_col_name] = df_annual[yoy_col_name].round(2)

    # add metadata columns
    df_annual["table_description"] = table_description
    df_annual["source"]            = "Statistics Canada WDS API"
    df_annual["load_timestamp"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df_annual


# -------------------------------------------------------
# Main — runs when you execute this script directly
# -------------------------------------------------------

if __name__ == "__main__":

    # make sure silver folder exists before saving
    os.makedirs("data/silver", exist_ok=True)

    print("Starting BOC transformations...")

    # transform each BOC series using the same reusable function
    # each gets a meaningful column name instead of the cryptic 'v'
    df_policy_rate = transform_boc_series(BRONZE_BOC_POLICY_RATE, "policy_rate_pct")
    df_cpi         = transform_boc_series(BRONZE_BOC_CPI,         "cpi_index")
    df_yield_2yr   = transform_boc_series(BRONZE_BOC_YIELD_2YR,   "bond_yield_2yr_pct")
    df_yield_10yr  = transform_boc_series(BRONZE_BOC_YIELD_10YR,  "bond_yield_10yr_pct")

    # merge all BOC series into one table on year
    # this gives us one row per year with all BOC metrics together
    # df_boc = df_policy_rate.merge(df_cpi, on="year", suffixes=("", "_cpi"))
    # df_boc = df_boc.merge(df_yield_2yr,  on="year", suffixes=("", "_2yr"))
    # df_boc = df_boc.merge(df_yield_10yr, on="year", suffixes=("", "_10yr"))

    # outer join — keep all years even if some metrics have no data
    # this preserves 2005-2008 rows where policy rate is null
    df_boc = df_policy_rate.merge(df_cpi,        on="year", how="outer", suffixes=("", "_cpi"))
    df_boc = df_boc.merge(df_yield_2yr,          on="year", how="outer", suffixes=("", "_2yr"))
    df_boc = df_boc.merge(df_yield_10yr,         on="year", how="outer", suffixes=("", "_10yr"))

    # keep only the columns we need — drop duplicate metadata columns from merges
    df_boc = df_boc[["year", "policy_rate_pct", "cpi_index", 
                      "bond_yield_2yr_pct", "bond_yield_10yr_pct",
                      "source", "load_timestamp"]]

    # fill metadata for all rows including outer joined years
    df_boc["source"]         = "Bank of Canada Valet API"
    df_boc["load_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # save to silver
    df_boc.to_csv(SILVER_BOC_RATES, index=False)
    print(f"Saved {len(df_boc)} rows to {SILVER_BOC_RATES}")

    print("BOC transformation complete.")

    print("Starting StatsCan transformations...")

    # transform housing price index
    df_housing = transform_statcan_series(
        BRONZE_STATCAN_HPI,
        "housing_price_index",
        "New Housing Price Index — Canada Total (house and land). Base year Dec 2016=100."
    )
    df_housing.to_csv(SILVER_STATCAN_HOUSING, index=False)
    print(f"Saved {len(df_housing)} rows to {SILVER_STATCAN_HOUSING}")

    # transform construction cost index — toronto proxy
    df_construction = transform_statcan_series(
        BRONZE_STATCAN_CONSTRUCTION,
        "construction_cost_index",
        "Building Construction Price Index — Toronto as national proxy. Base year 2023=100."
    )
    # filter construction cost to match our analysis period 2005 onwards
    df_construction = df_construction[df_construction["year"] >= 2005]

    df_construction.to_csv(SILVER_STATCAN_CONSTRUCTION, index=False)
    print(f"Saved {len(df_construction)} rows to {SILVER_STATCAN_CONSTRUCTION}")

    print("StatsCan transformation complete.")