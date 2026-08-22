import pandas as pd
import json
import os
from datetime import datetime

# -------------------------------------------------------
# Configuration — file paths for bronze and silver layers
# Add new sources here without touching the functions below
# -------------------------------------------------------

# 1. input paths — raw bronze files
BRONZE_BOC_POLICY_RATE = "data/bronze/boc_policy_rate_raw.json"
BRONZE_BOC_CPI         = "data/bronze/boc_inflation_cpi_raw.json"
BRONZE_BOC_YIELD_2YR   = "data/bronze/boc_bond_yield_2yr_raw.json"
BRONZE_BOC_YIELD_10YR  = "data/bronze/boc_bond_yield_10yr_raw.json"

# output paths — clean silver files
SILVER_BOC_RATES       = "data/silver/silver_boc_rates.csv"

# 2. StatsCan bronze input paths
BRONZE_STATCAN_HPI          = "data/bronze/statcan_housing_price_index_raw.json"
BRONZE_STATCAN_CONSTRUCTION = "data/bronze/statcan_construction_cost_toronto_raw.json"

# StatsCan silver output paths
SILVER_STATCAN_HOUSING      = "data/silver/silver_statcan_housing.csv"
SILVER_STATCAN_CONSTRUCTION = "data/silver/silver_statcan_construction.csv"

# 3. OSFI bronze input paths — three files covering different periods
BRONZE_OSFI_PC1 = "data/bronze/property_and_casualty_companies_quarterly_1_raw.csv"
BRONZE_OSFI_1Q  = "data/bronze/property_and_casualty_companies_quarterly_1q_raw.csv"
BRONZE_OSFI_PC2 = "data/bronze/property_and_casualty_companies_quarterly_pc2_raw.csv"

# IBC bronze input path
BRONZE_IBC_CAT  = "data/bronze/ibc_catastrophe_losses_raw.csv"

# OSFI and IBC silver output paths
SILVER_OSFI     = "data/silver/silver_osfi_insurance.csv"
SILVER_IBC      = "data/silver/silver_ibc_catastrophe.csv"

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
# Table: silver_osfi_insurance
# Description: Annual P&C insurance industry metrics —
#              net earned premiums, net claims incurred,
#              and loss ratio for Total Canadian P&C.
#              Source: OSFI Open Government Portal
#              Granularity: One row per year (2005 - present)
#              Key column: year (integer, unique, not null)
#              Note: Three source files with different metric
#              names due to IFRS 17 accounting change in 2023.
#              Loss ratio calculated for PC2 (post 2023).
# -------------------------------------------------------

def transform_osfi_file(filepath, metric_map, is_quarterly=True, file_source=None):
    """
    REUSABLE: Cleans one OSFI file from bronze.
    - Filters for Total Canadian P&C industry only
    - Filters Q4 only for quarterly files (year end figures)
    - Extracts premiums, claims, loss ratio using metric_map
    - Standardizes column names across all three files
    - Returns clean annual dataframe

    metric_map: dictionary mapping standard names to file specific labels
    Example: {"premiums": "Total NEP", "claims": "Net claims incurred current year", 
               "loss_ratio": "Total claims ratio"}
    is_quarterly: True for 1Q and PC2 files, False for PC1 annual file
    """

    print(f"  Reading {filepath}...")

    # read in chunks — OSFI files are large (100MB to 1GB)
    chunks = []
    for chunk in pd.read_csv(filepath, chunksize=100000,
                              encoding="utf-8-sig", low_memory=False):

        # filter for Total Canadian P&C industry only
        chunk = chunk[chunk["Total P&C Companies/FIs"] == "Total Canadian Property & Casualty"]

        # filter Q4 only for quarterly files — Q4 = full year cumulative figure
        if is_quarterly:
            chunk = chunk[chunk["Fiscal Quarter"].str.startswith("Q4")]

        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    print(f"  Filtered to {len(df)} rows")

    # extract each metric by its label name in this specific file
    results = {}

    for standard_name, label in metric_map.items():
        # filter for this specific metric label
        metric_df = df[df["Data Point Address Label"] == label][
            ["Fiscal Year/Année fiscale", "Measure Value/Valeur de mesure"]
        ].copy()

        # rename columns to standard names
        metric_df.columns = ["year", standard_name]

        # convert to numeric — handles any string values
        metric_df[standard_name] = pd.to_numeric(
            metric_df[standard_name], errors="coerce"
        )

        results[standard_name] = metric_df

    # merge all metrics on year
    df_merged = results["premiums_nep"]
    for key in ["claims_incurred", "loss_ratio"]:
        if key in results:
            df_merged = df_merged.merge(results[key], on="year", how="outer")

    # add file source so we always know which OSFI file each row came from
    if file_source:
        df_merged["osfi_file_source"] = file_source
    
    return df_merged


    # -------------------------------------------------------
# Table: silver_ibc_catastrophe
# Description: Annual total insured catastrophic losses
#              in Canada. Used to flag years where catastrophe
#              events distorted claims data — separates
#              rate cycle signal from catastrophe noise.
#              Source: IBC/CatIQ annual press releases
#              Granularity: One row per year (2005 - present)
#              Key column: year (integer, unique, not null)
# -------------------------------------------------------

def transform_ibc(bronze_path):
    """
    Cleans IBC catastrophe loss CSV from bronze.
    - Reads manually curated CSV
    - Standardizes column names
    - Adds high catastrophe year flag for dashboard use
    - Adds source and load timestamp
    """

    df = pd.read_csv(bronze_path)

    # standardize column names to lowercase with underscores
    df = df.rename(columns={
        "year": "year",
        "catastrophe_losses_billions_cad": "cat_losses_billions",
        "major_events": "major_events",
        "data_source": "data_source",
        "notes": "notes"
    })

    # flag high catastrophe years — above $3B threshold
    # these are years where catastrophes may distort the rate cycle signal
    df["high_cat_year"] = df["cat_losses_billions"].apply(
        lambda x: True if x >= 3.0 else False
    )

    # add metadata
    df["source"]         = "IBC/CatIQ Annual Press Releases"
    df["load_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df


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


    print("Starting OSFI transformations...")

    # metric mapping for PC1 file (1996-2013)
    pc1_metrics = {
        "premiums_nep":    "Total NEP",
        "claims_incurred": "Net claims incurred current year",
        "loss_ratio":      "Total claims ratio"
    }

    # metric mapping for 1Q file (2015-2023)
    q1_metrics = {
        "premiums_nep":    "NEP -  TOTAL",
        "claims_incurred": "Net Claims and Adj. Exp.",  # different label in 1Q file
        "loss_ratio":      "Total claims ratio"
    }

    # metric mapping for PC2 file (2023-2026)
    # loss ratio not published — calculated after merge
    pc2_metrics = {
        "premiums_nep":    "PC2: Total Insurance Revenue, Current Period",
        "claims_incurred": "PC2:  TOTAL, Insurance Service Expenses, Incurred Claims and Other Insurance Service Expenses"
    }

    # transform all three files
    df_pc1 = transform_osfi_file(BRONZE_OSFI_PC1, pc1_metrics, is_quarterly=False, file_source="PC1 Annual 1996-2013")
    df_1q  = transform_osfi_file(BRONZE_OSFI_1Q,  q1_metrics,  is_quarterly=True,  file_source="1Q Quarterly 2015-2023")
    df_pc2 = transform_osfi_file(BRONZE_OSFI_PC2, pc2_metrics, is_quarterly=True,  file_source="PC2 Quarterly 2023-2026")

    # calculate loss ratio for PC2 — claims / premiums * 100
    df_pc2["loss_ratio"] = (
        df_pc2["claims_incurred"] / df_pc2["premiums_nep"] * 100
    ).round(2)

    # filter each file to its correct date range before combining
    df_pc1 = df_pc1[df_pc1["year"].between(2005, 2013)]
    df_1q  = df_1q[df_1q["year"].between(2014, 2022)]
    df_pc2 = df_pc2[df_pc2["year"] >= 2023]

    # stack all three files on top of each other — no overlaps now
    df_osfi = pd.concat([df_pc1, df_1q, df_pc2], ignore_index=True)

    # flag accounting standard per year — important for interpretation
    # IFRS 4 to IFRS 17 transition creates a break at 2024
    # direct year over year comparison across 2023-2024 should be interpreted with caution
    df_osfi["accounting_standard"] = df_osfi["year"].apply(
        lambda x: "IFRS 17" if x >= 2023 else "IFRS 4"
    )


    # sort by year
    df_osfi = df_osfi.sort_values("year").reset_index(drop=True)

    # add metadata
    df_osfi["source"]         = "OSFI Open Government Portal"
    df_osfi["load_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # save to silver
    df_osfi.to_csv(SILVER_OSFI, index=False)
    print(f"Saved {len(df_osfi)} rows to {SILVER_OSFI}")

    print("OSFI transformation complete.")


    print("Starting IBC transformation...")

    df_ibc = transform_ibc(BRONZE_IBC_CAT)
    df_ibc.to_csv(SILVER_IBC, index=False)
    print(f"Saved {len(df_ibc)} rows to {SILVER_IBC}")

    print("IBC transformation complete.")

 