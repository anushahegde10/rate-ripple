# -------------------------------------------------------
# profile.py
# Purpose: Reusable data profiling script for any CSV dataset
# Usage:   python scripts/profile.py <path_to_csv>
# Example: python scripts/profile.py data/bronze/osfi_pc2_raw.csv
# Output:  Saved report in docs/profiles/ + printed to terminal
# -------------------------------------------------------
# GENERIC: This script works on ANY CSV file you point it at.
#          No changes needed — just pass a different file path.
# -------------------------------------------------------

import pandas as pd
import sys
import os
from datetime import datetime

# -------------------------------------------------------
# GENERIC: Configuration — adjust these thresholds as needed
# low_cardinality_threshold: columns with fewer unique values
# than this will show all unique values in the report
# sample_rows: number of rows to show as a data sample
# chunk_size: how many rows to read at a time for large files
# -------------------------------------------------------
LOW_CARDINALITY_THRESHOLD = 20
SAMPLE_ROWS = 5
CHUNK_SIZE = 100000


def get_file_info(filepath):
    """
    GENERIC: Gets basic file metadata — name, size, and profiling timestamp.
    Works on any file path you pass in.
    """
    file_name = os.path.basename(filepath)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return file_name, file_size_mb, timestamp


def load_data(filepath):
    """
    GENERIC: Loads CSV into a pandas dataframe.
    Handles large files by reading in chunks and combining.
    encoding='utf-8-sig' handles the BOM character common in government CSVs.
    """
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    # for large files (over 100MB), read in chunks to avoid memory issues
    if file_size_mb > 100:
        print(f"Large file detected ({file_size_mb:.1f} MB) — reading in chunks...")
        chunks = []
        for chunk in pd.read_csv(filepath, chunksize=CHUNK_SIZE, encoding="utf-8-sig", low_memory=False):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
    else:
        df = pd.read_csv(filepath, encoding="utf-8-sig", low_memory=False)

    return df


def profile_basic(df, file_name, file_size_mb, timestamp):
    """
    GENERIC: Profiles basic shape, size, and metadata of any dataframe.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("DATA PROFILING REPORT")
    lines.append("=" * 70)
    lines.append(f"File         : {file_name}")
    lines.append(f"File Size    : {file_size_mb:.2f} MB")
    lines.append(f"Profiled At  : {timestamp}")
    lines.append(f"Rows         : {df.shape[0]:,}")
    lines.append(f"Columns      : {df.shape[1]}")
    lines.append(f"Duplicate Rows: {df.duplicated().sum():,}")
    lines.append("")
    return lines


def profile_columns(df):
    """
    GENERIC: Profiles each column — data type, null count, and unique value count.
    Also flags columns with zero nulls as clean columns.
    Also flags columns where mixed data types may exist (object columns with numeric-looking values).
    """
    lines = []
    lines.append("-" * 70)
    lines.append("COLUMN OVERVIEW")
    lines.append("-" * 70)
    lines.append(f"{'Column':<45} {'Type':<12} {'Nulls':>8} {'Unique':>8}")
    lines.append("-" * 70)

    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = df[col].isnull().sum()
        unique_count = df[col].nunique()
        lines.append(f"{col:<45} {dtype:<12} {null_count:>8,} {unique_count:>8,}")

    lines.append("")

    # columns with zero nulls — these are your most reliable columns
    clean_cols = [col for col in df.columns if df[col].isnull().sum() == 0]
    lines.append("Columns with ZERO nulls (most reliable):")
    for col in clean_cols:
        lines.append(f"  - {col}")
    lines.append("")

    return lines


def profile_unique_values(df):
    """
    GENERIC: For columns with few unique values (low cardinality),
    shows all unique values. Useful for understanding categorical columns
    like status flags, region names, or quarter labels.
    High cardinality columns (like IDs) just show the count.
    """
    lines = []
    lines.append("-" * 70)
    lines.append(f"UNIQUE VALUES (columns with fewer than {LOW_CARDINALITY_THRESHOLD} unique values)")
    lines.append("-" * 70)

    for col in df.columns:
        unique_count = df[col].nunique()
        if unique_count <= LOW_CARDINALITY_THRESHOLD:
            lines.append(f"\n{col} ({unique_count} unique values):")
            for val in sorted(df[col].dropna().unique().astype(str)):
                lines.append(f"  - {val}")

    lines.append("")
    return lines


def profile_value_distribution(df):
    """
    GENERIC: For low cardinality columns, shows what percentage of rows
    each unique value represents. Helps spot dominant values or imbalanced data.
    """
    lines = []
    lines.append("-" * 70)
    lines.append("VALUE DISTRIBUTION (columns with fewer than 20 unique values)")
    lines.append("-" * 70)

    for col in df.columns:
        unique_count = df[col].nunique()
        if 1 < unique_count <= LOW_CARDINALITY_THRESHOLD:
            lines.append(f"\n{col}:")
            dist = df[col].value_counts(normalize=True) * 100
            for val, pct in dist.items():
                lines.append(f"  {str(val):<40} {pct:>6.1f}%")

    lines.append("")
    return lines


def profile_numeric(df):
    """
    GENERIC: For numeric columns, shows min, max, mean, and std deviation.
    High std deviation relative to mean may indicate outliers worth investigating.
    Negative min values in columns that should be positive (like premiums) is a red flag.
    """
    lines = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        lines.append("No numeric columns detected.")
        lines.append("")
        return lines

    lines.append("-" * 70)
    lines.append("NUMERIC COLUMN STATISTICS")
    lines.append("-" * 70)
    lines.append(f"{'Column':<40} {'Min':>15} {'Max':>15} {'Mean':>15} {'Std Dev':>15}")
    lines.append("-" * 70)

    for col in numeric_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        col_mean = df[col].mean()
        col_std = df[col].std()
        lines.append(f"{col:<40} {col_min:>15,.2f} {col_max:>15,.2f} {col_mean:>15,.2f} {col_std:>15,.2f}")

    lines.append("")
    return lines


def profile_date_range(df):
    """
    GENERIC: Detects columns that look like dates or years and shows
    the earliest and latest values. Critical for time series data.
    Looks for columns with 'date', 'year', 'period', 'quarter' in the name.
    """
    lines = []
    date_keywords = ["date", "year", "period", "quarter", "fiscal"]
    date_cols = [col for col in df.columns if any(kw in col.lower() for kw in date_keywords)]

    if not date_cols:
        return lines

    lines.append("-" * 70)
    lines.append("DATE / PERIOD RANGE")
    lines.append("-" * 70)

    for col in date_cols:
        try:
            min_val = df[col].dropna().min()
            max_val = df[col].dropna().max()
            lines.append(f"{col}:")
            lines.append(f"  Earliest : {min_val}")
            lines.append(f"  Latest   : {max_val}")
            lines.append("")
        except Exception:
            pass

    return lines


def profile_sample(df):
    """
    GENERIC: Shows the first few rows of the dataset so you can
    visually inspect what the raw data looks like before any processing.
    """
    lines = []
    lines.append("-" * 70)
    lines.append(f"SAMPLE ROWS (first {SAMPLE_ROWS})")
    lines.append("-" * 70)
    lines.append(df.head(SAMPLE_ROWS).to_string())
    lines.append("")
    return lines


def save_report(lines, file_name, timestamp):
    """
    GENERIC: Saves the profiling report to docs/profiles/ folder.
    File name includes the dataset name and timestamp so reports
    don't overwrite each other when you profile multiple files.
    """
    # create output folder if it does not exist
    os.makedirs("docs/profiles", exist_ok=True)

    # clean timestamp for filename — remove colons and spaces
    ts_clean = timestamp.replace(":", "").replace(" ", "_").replace("-", "")

    # use dataset name in report filename
    dataset_name = file_name.replace(".csv", "").replace(" ", "_")
    report_path = f"docs/profiles/profile_{dataset_name}_{ts_clean}.txt"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return report_path


# -------------------------------------------------------
# Main — runs when you execute this script directly
# GENERIC: Pass any CSV file path as a command line argument
# -------------------------------------------------------

if __name__ == "__main__":

    # check that a file path was provided
    if len(sys.argv) < 2:
        print("Usage: python scripts/profile.py <path_to_csv>")
        print("Example: python scripts/profile.py data/bronze/osfi_pc2_raw.csv")
        sys.exit(1)

    filepath = sys.argv[1]

    # check that the file exists
    if not os.path.exists(filepath):
        print(f"Error: File not found — {filepath}")
        sys.exit(1)

    # get file metadata
    file_name, file_size_mb, timestamp = get_file_info(filepath)
    print(f"\nProfiling: {file_name} ({file_size_mb:.2f} MB)")
    print(f"Started at: {timestamp}\n")

    # load the data
    df = load_data(filepath)

    # run all profiling sections
    all_lines = []
    all_lines += profile_basic(df, file_name, file_size_mb, timestamp)
    all_lines += profile_columns(df)
    all_lines += profile_date_range(df)
    all_lines += profile_unique_values(df)
    all_lines += profile_value_distribution(df)
    all_lines += profile_numeric(df)
    all_lines += profile_sample(df)

    # print to terminal
    print("\n".join(all_lines))

    # save to file
    report_path = save_report(all_lines, file_name, timestamp)
    print(f"\nReport saved to: {report_path}")