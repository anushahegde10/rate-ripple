# Architecture Decision Record (ADR)
## The Rate Ripple — Data Pipeline Architecture

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| V1.0 | May 2026 | Senior Analytics Professional | Initial ADR |

---

## 1. System Overview

The Rate Ripple is a production-grade analytics pipeline at small scale. It pulls data from four Canadian public data sources, transforms it through a Medallion architecture, stores it in PostgreSQL, and delivers insights through a Tableau dashboard.

```
Data Sources          Bronze           Silver           Gold            Consume
─────────────         ──────           ──────           ────            ───────
BOC API          →                                                   
Stats Canada     →    Raw files   →    Cleaned     →    Joined      →   Tableau
OSFI             →    No changes       Standardized     Business        Dashboard
IBC              →    Local only       Annual avg        ready          + AI Layer
```

---

## 2. Folder Structure

```
rate-ripple/
├── data/
│   ├── bronze/          # Raw files from APIs and downloads — never modified
│   ├── silver/          # Cleaned, standardized, annual granularity
│   └── gold/            # Final joined analytical dataset
├── scripts/
│   ├── extract.py       # Pulls data from all sources → saves to bronze
│   ├── transform.py     # Cleans bronze → saves to silver
│   ├── load.py          # Loads silver → upserts to PostgreSQL gold
│   ├── validate.py      # Row count checks and logging after each step
│   └── run_pipeline.py  # Master script — runs full pipeline end to end
├── notebooks/           # Jupyter notebooks for exploration and analysis
├── sql/                 # SQL queries answering each business question
├── dashboard/           # Tableau output files and published links
├── docs/                # PRD, ADR, project charter, notes
└── config/              # Database connection config — never pushed to GitHub
```

---

## 3. Architecture Decisions

### ADR-001 — PostgreSQL as the Analytical Data Store

**Decision:** Use PostgreSQL running in Docker as the primary data store.

**Why:**
PostgreSQL is the same enterprise-grade database used by Big 5 banks and fintechs in production. Using it here means every pattern built — connections, upserts, schemas, SQL queries — is directly transferable to a production environment. This project is designed as a reusable framework, not a one-off script.

**Alternatives considered:**
- CSV files — simple but not queryable, not scalable, no data integrity
- SQLite — lightweight but not production equivalent
- Cloud database — unnecessary cost and complexity for a portfolio project

**Tradeoff:** Requires Docker to be running locally. Acceptable for this scale.

---

### ADR-002 — Medallion Architecture (Bronze / Silver / Gold)

**Decision:** Implement a three-layer Medallion architecture for all data transformations.

**Why:**
Medallion is the industry standard for layered data pipelines. Each layer has a clear responsibility:

| Layer | Responsibility | Storage |
|-------|---------------|---------|
| Bronze | Raw source data — never modified | Local files in data/bronze/ |
| Silver | Cleaned, standardized, annual averages calculated | Local files in data/silver/ |
| Gold | Final joined table — rate + housing + insurance | PostgreSQL — feeds Tableau |

Each layer is independently rerunnable and auditable. If something breaks in silver, bronze is always intact. If gold needs to be rebuilt, silver is always clean and ready.

**Alternatives considered:**
- Load raw data directly to PostgreSQL — loses auditability, harder to debug
- Two layers only — loses the clean separation between raw and cleaned data

---

### ADR-003 — Idempotent Pipeline Design

**Decision:** All pipeline steps are designed to be idempotent — safe to run multiple times without creating duplicates or corrupting data.

**Why:**
This is a living project. The pipeline will be rerun regularly to pull the latest BOC rates and insurance data as new annual figures are published. Idempotency ensures that rerunning never creates duplicates or corrupts existing data.

**How it is implemented:**
- Bronze — always overwrite. Raw files are replaced on every run.
- Silver — always overwrite. Cleaned files are replaced on every run.
- Gold (PostgreSQL) — upsert on load. Insert if new year, update if exists. Never duplicate.

---

### ADR-004 — Annual Granularity

**Decision:** All datasets are standardized to annual granularity before loading to gold.

**Why:**
OSFI publishes P&C insurance data annually. Since the joining key across all datasets must be consistent, annual granularity was chosen for all sources. BOC API returns daily data — this is averaged to annual in the silver transformation step.

**Interview framing:**
"BOC rate changes occur intra-year. Annual averages are used for consistency with OSFI reporting granularity. Key rate cycle periods are flagged explicitly in the dashboard."

**Tradeoff:** Intra-year rate movements are smoothed. This is a documented, conscious decision — not a limitation.

---

### ADR-005 — Credentials Management

**Decision:** All credentials and connection details are stored in a .env file and config/db_config.ini — both excluded from GitHub via .gitignore.

**Why:**
Passwords and API keys must never be pushed to a public GitHub repository. All scripts reference environment variables, not hardcoded credentials.

**Files excluded from GitHub:**
```
.env
config/db_config.ini
data/bronze/*
data/silver/*
__pycache__/
*.pyc
```

---

## 4. Pipeline Flow

```
run_pipeline.py
│
├── 1. extract.py
│       ├── Call BOC Valet API → save to data/bronze/boc_rates_raw.json
│       ├── Download Stats Canada CSV → save to data/bronze/statcan_raw.csv
│       ├── Download OSFI data → save to data/bronze/osfi_raw.xlsx
│       └── Download IBC data → save to data/bronze/ibc_raw.csv
│
├── 2. transform.py
│       ├── Clean BOC data → annual average rate → data/silver/boc_rates.csv
│       ├── Clean Stats Canada → annual HPI, CPI → data/silver/housing.csv
│       ├── Clean OSFI → annual loss ratios → data/silver/insurance.csv
│       └── Clean IBC → catastrophe flags → data/silver/catastrophe.csv
│
├── 3. load.py
│       ├── Join all silver tables on year
│       ├── Upsert into PostgreSQL gold schema
│       └── Log row counts loaded
│
└── 4. validate.py
        ├── Check row counts in each gold table
        ├── Flag any years with missing data
        └── Write run log to docs/pipeline_log.txt
```

---

## 5. Technology Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.x | Data extraction and transformation |
| PostgreSQL | 16 | Analytical data store — gold layer |
| Docker | Latest | Runs PostgreSQL in isolated container |
| Tableau Public | Latest | Dashboard and visualization |
| Git + GitHub | Latest | Version control and portfolio publishing |

---

## 6. Future Extensions

| Extension | ADR Impact |
|-----------|------------|
| AI natural language layer | New script ai_query.py — connects LLM to gold layer |
| Predictive analytics | New notebook in notebooks/ — reads from gold layer |
| Mortgage default project | Same pipeline structure — new Docker container, new database |
| Provincial breakdown | Silver transform updated — no architectural change |

---

*This is a living document. Updated as architectural decisions evolve.*
