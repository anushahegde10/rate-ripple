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

# BOC series code for the overnight policy rate
BOC_SERIES = "V39079"

# API endpoint — we inject the series code and dates dynamically
BOC_URL = f"https://www.bankofcanada.ca/valet/observations/{BOC_SERIES}/json?start_date={START_DATE}&end_date={END_DATE}"

# Where to save the raw file — bronze layer, no changes
BRONZE_PATH = "data/bronze/boc_rates_raw.json"

# -------------------------------------------------------
# Extract BOC policy rate data from the Valet API
# Saves raw JSON response to bronze . The data is as is data with no changes
# -------------------------------------------------------

def extract_boc_rates():
    
    print(f"Calling BOC API for rates from {START_DATE} to {END_DATE}...")
    
    # make the API call
    response = requests.get(BOC_URL)
    
    # stop immediately if something went wrong
    if response.status_code != 200:
        raise Exception(f"BOC API call failed. Status code: {response.status_code}")
    
    # parse the JSON response
    raw_data = response.json()
    
    # grab only the observations . No need of terms or seriesDetail
    observations = raw_data["observations"]
    
    print(f"Retrieved {len(observations)} daily records from BOC API")
    
    # save raw observations to bronze exactly as received, no changes
    with open(BRONZE_PATH, "w") as f:
        json.dump(observations, f, indent=2)
    
    print(f"Raw data saved to {BRONZE_PATH}")

    # -------------------------------------------------------
# Main — runs when you execute this script directly
# -------------------------------------------------------

if __name__ == "__main__":
    
    # make sure bronze folder exists before saving
    os.makedirs("data/bronze", exist_ok=True)
    
    # run the extraction
    extract_boc_rates()
    
    print("BOC extraction complete.")
