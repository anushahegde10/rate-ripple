# -------------------------------------------------------
# data_search.py
# Purpose: Search any CSV column for keyword matches
# Usage:   python scripts/data_search.py <file> "<column>" "<keywords>"
# Example: python scripts/data_search.py data/bronze/osfi_pc2_raw.csv 
#          "Data Point Address Label" "premium,claims,loss"
# GENERIC: Works on any CSV file — not specific to this project
# -------------------------------------------------------

import pandas as pd
import sys
import os

def search_column(filepath, column_name, keywords):
    """
    GENERIC: Searches a specific column in any CSV for keyword matches.
    Returns all unique values that contain any of the keywords.
    Case insensitive search.
    """
    
    # split keywords by comma
    keyword_list = [k.strip().lower() for k in keywords.split(",")]
    
    print(f"\nSearching '{column_name}' for: {keyword_list}")
    print(f"File: {filepath}\n")
    
    # read in chunks for large files
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    
    if file_size_mb > 100:
        print(f"Large file ({file_size_mb:.1f} MB) — reading in chunks...")
        chunks = []
        for chunk in pd.read_csv(filepath, chunksize=100000, 
                                  encoding="utf-8-sig", low_memory=False,
                                  usecols=[column_name]):
            chunks.append(chunk)
        df = pd.concat(chunks)
    else:
        df = pd.read_csv(filepath, encoding="utf-8-sig", 
                         low_memory=False, usecols=[column_name])
    
    # get unique values in that column
    unique_values = df[column_name].dropna().unique()
    
    # filter for keyword matches — case insensitive
    matches = [v for v in unique_values 
               if any(kw in str(v).lower() for kw in keyword_list)]
    
    # print results
    print(f"Found {len(matches)} matches:\n")
    for match in sorted(matches):
        print(f"  {match}")
    
    return matches

# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":
    
    if len(sys.argv) < 4:
        print("Usage: python scripts/data_search.py <file> <column> <keywords>")
        print("Example: python scripts/data_search.py data/bronze/file.csv \"Column Name\" \"premium,claims\"")
        sys.exit(1)
    
    filepath    = sys.argv[1]
    column_name = sys.argv[2]
    keywords    = sys.argv[3]
    
    if not os.path.exists(filepath):
        print(f"Error: File not found — {filepath}")
        sys.exit(1)
    
    search_column(filepath, column_name, keywords)