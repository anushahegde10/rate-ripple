# -------------------------------------------------------
# extract.py
# Purpose: Pull raw data from public Canadian data sources
# and save to bronze layer with no transformations
# Sources: Bank of Canada Valet API - bankofcanada.ca/valet
# -------------------------------------------------------

import requests   # makes HTTP calls to APIs
import json       # reads and writes JSON data
import os         # handles file paths and folders
from datetime import date      # gets today's date dynamically
from dotenv import load_dotenv # loads credentials from .env file safely

# -------------------------------------------------------
# Configuration — all settings in one place
# Change dates or paths here without touching the logic
# -------------------------------------------------------

load_dotenv()  # load any credentials from .env file

# Date range - 2005 to today gives us 20 years of rate cycles
START_DATE = "2005-01-01"
END_DATE = date.today().strftime("%Y-%m-%d")  # always pulls latest data

# BOC series codes — add new ones here without touching the logic below
BOC_SERIES = {
    "policy_rate": "V39079",       # overnight rate - the main rate ripple trigger
    "inflation_cpi": "V41690914" ,  # total CPI tracks inflation driven by rate cycle
    "bond_yield_2yr": "BD.CDN.2YR.DQ.YLD",    # short term — tracks rate expectations
    "bond_yield_10yr": "BD.CDN.10YR.DQ.YLD"   # long term — tracks growth outlook
}


# Statistics Canada vector IDs — same concept as BOC series codes
STATCAN_VECTORS = {
    "housing_price_index": "v111955442" , # new housing price index — total canada
    "construction_cost_toronto": "v1617912756"   # building construction price index — toronto as national proxy
}


# API endpoint — we inject the series code and dates dynamically
#BOC_URL = f"https://www.bankofcanada.ca/valet/observations/{BOC_SERIES}/json?start_date={START_DATE}&end_date={END_DATE}"

# Where to save the raw file — bronze layer, no changes
#BRONZE_PATH = "data/bronze/boc_rates_raw.json"  -- Commented as no need of single URL and [path]



# -------------------------------------------------------
# Extract BOC policy rate data from the Valet API
# Saves raw JSON response to bronze . The data is as is data with no changes
# -------------------------------------------------------

def extract_boc_series(name, series_code):
    # builds the API url dynamically for any series code we pass in
    url = f"https://www.bankofcanada.ca/valet/observations/{series_code}/json?start_date={START_DATE}&end_date={END_DATE}"
    
    print(f"Calling BOC API for {name} ({series_code})...")
    
    response = requests.get(url)
    
    # stop immediately if something went wrong
    if response.status_code != 200:
        raise Exception(f"BOC API call failed for {name}. Status code: {response.status_code}")
    
    raw_data = response.json()
    
    # grab only the observations — ignore terms and seriesDetail
    observations = raw_data["observations"]
    
    print(f"Retrieved {len(observations)} records for {name}")
    
    # save each series as its own file in bronze
    bronze_path = f"data/bronze/boc_{name}_raw.json"
    with open(bronze_path, "w") as f:
        json.dump(observations, f, indent=2)
    
    print(f"Saved to {bronze_path}")


# -------------------------------------------------------
# Extract Statistics Canada data using vector ID
# StatsCan API needs vector ID + number of periods
# Saves raw JSON response to bronze — no changes
# -------------------------------------------------------

def extract_statcan_series(name, vector_id):
    # StatsCan API returns latest N periods — we calculate how many months since 2005
    periods = 252  # 21 years x 12 months = enough to cover 2005 to today

    url = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
    
    # StatsCan API requires a POST request with vector ID and periods
    payload = [{"vectorId": int(vector_id.replace("v", "")), "latestN": periods}]
    
    print(f"Calling StatsCan API for {name} ({vector_id})...")
    
    response = requests.post(url, json=payload)
    
    # stop immediately if something went wrong
    if response.status_code != 200:
        raise Exception(f"StatsCan API call failed for {name}. Status code: {response.status_code}")
    
    raw_data = response.json()
    
    print(f"Retrieved data for {name}")
    
    # save raw response to bronze — no changes
    bronze_path = f"data/bronze/statcan_{name}_raw.json"
    with open(bronze_path, "w") as f:
        json.dump(raw_data, f, indent=2)
    
    print(f"Saved to {bronze_path}")

# -------------------------------------------------------
# Main — runs when you execute this script directly
# -------------------------------------------------------

if __name__ == "__main__":
    
    # make sure bronze folder exists before saving
    os.makedirs("data/bronze", exist_ok=True)
    
    # loop through all BOC series and extract each one
    for name, series_code in BOC_SERIES.items():
        extract_boc_series(name, series_code)
    
    print("All BOC extractions complete.")

        # loop through all StatsCan series and extract each one
    for name, vector_id in STATCAN_VECTORS.items():
        extract_statcan_series(name, vector_id)
    
    print("All StatsCan extractions complete.")
