# Product Requirements Document (PRD)
## The Rate Ripple — Tracking How Bank of Canada Decisions Flow Into Property Insurance Risk

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| V1.0 | May 2026 | Senior Analytics Professional | Initial PRD |

---

## 1. Project Vision

Enable actuaries and underwriters to understand how Bank of Canada rate cycles have historically impacted P&C loss ratios — so they can anticipate risk exposure during future rate changes.

Provide a data-backed historical foundation for pricing decisions, reserve setting, and revenue forecasting across different rate environments.

---

## 2. Problem Statement

Canada experienced one of its most aggressive interest rate cycles in modern history between 2022 and 2023. The Bank of Canada raised its policy rate from 0.25% to 5.00% in under 18 months.

This rate cycle rippled through the Canadian economy in a chain reaction:

```
BOC Rates Rise
    → Mortgage payments increase
    → Homeowners defer maintenance
    → Small problems become large claims
    → Inflation raises rebuild costs
    → Insurers raise premiums
    → Homeowners squeezed further
```

Behind every loss ratio is a homeowner whose quality of life depends on the system working.

Despite this clear connection, the relationship between monetary policy cycles and P&C insurance risk is rarely analyzed in an integrated, data-driven way. This project fills that gap using real Canadian public data.

---

## 3. Users & Stakeholders

| User Type | Role | What They Need |
|-----------|------|----------------|
| **Primary** | Actuaries | Historical loss ratio trends by rate environment to inform pricing models |
| **Primary** | Underwriters | Risk exposure patterns during rate cycle peaks to adjust policy terms |
| **Secondary** | Risk Managers / CRO | Stress testing and reserving decisions across economic cycles |
| **Executive** | CFO / CEO | High level dashboard summary — rate cycle impact on company financials |

---

## 4. Business Questions This Product Answers

| # | Business Question | Why It Matters |
|---|-------------------|----------------|
| Q1 | What did the Canadian rate cycle look like over the last 15 years? | Sets the macroeconomic context for all downstream analysis |
| Q2 | When rates rise, what happens to Canadian property values and housing stress? | Rising rates compress affordability — a leading indicator of insurance risk |
| Q3 | Do P&C insurance claims and loss ratios rise during high rate periods? | Tests whether rate cycles are a predictive signal for claims |
| Q4 | Does inflation increase claim costs even when volumes stay flat? | Construction cost inflation means fewer claims can still cost significantly more |
| Q5 | Now that rates are declining, what risks remain for Canadian P&C insurers? | Forward-looking business judgment — separates analysis from insight |

---

## 5. MoSCoW Requirements

### Must Have — Core product. Without these, the project does not exist.

- [ ] Real data pulled from live public APIs (Bank of Canada, Statistics Canada, OSFI, IBC)
- [ ] Ability to refresh the pipeline anytime and get latest data
- [ ] Medallion architecture — Bronze, Silver, Gold layers
- [ ] PostgreSQL as the analytical data store
- [ ] Tableau dashboard showing rate cycle impact on insurance loss ratios
- [ ] All 5 business questions answered with data-backed evidence
- [ ] GitHub repository — clean, documented, publicly accessible

### Should Have — Important but project works without them on day one.

- [ ] Pipeline logging — every run writes a log with row counts and status
- [ ] Pipeline validation — row count checks after every load step
- [ ] AI natural language layer — executives can ask business questions in plain English
- [ ] Predictive analytics — loss ratio forecasting based on rate scenarios

### Could Have — Nice to have if time permits.

- [ ] Mortgage default extension using the same pipeline framework
- [ ] Regional breakdown by province
- [ ] Auto and life insurance segments alongside P&C
- [ ] Catastrophe event overlay from IBC as a separate dashboard panel

### Won't Have — Explicitly out of scope for this version.

- Individual insurer level data — not publicly available
- Real time streaming — annual data granularity does not require it
- Mobile optimized dashboard — handled by Tableau Public natively

---

## 6. Data Sources

| Source | Data | Access | Layer |
|--------|------|--------|-------|
| Bank of Canada Valet API | Policy rate history | Free REST API | Bronze → Silver → Gold |
| Statistics Canada | Housing Price Index, CPI, construction costs | Free CSV + API | Bronze → Silver → Gold |
| OSFI | P&C premiums, claims, loss ratios | Free Excel/PDF | Bronze → Silver → Gold |
| Insurance Bureau of Canada | Catastrophic loss events | Free public reports | Bronze → Silver → Gold |

---

## 7. Success Metrics

This project is successful when:

1. All 5 business questions are answered with real Canadian data
2. An actuary can open the Tableau dashboard and understand rate cycle impact on loss ratios in under 2 minutes — without explanation
3. The pipeline can be rerun anytime without creating duplicates or corrupting data
4. The GitHub repository is clean, documented, and tells the full story
5. The project can be explained confidently to both a business executive and a technical engineer

---

## 8. Assumptions & Constraints

**Assumptions**
- Annual data granularity is sufficient to identify meaningful rate cycle trends
- OSFI industry-level data is representative of the broader Canadian P&C market
- A 6-12 month lag between rate changes and insurance claim response is assumed

**Constraints**
- OSFI public data is industry-level only — individual insurer data is not publicly available
- Causal relationships cannot be definitively proven — this project identifies correlations and patterns
- Regional granularity is limited to provincial level based on available public data

---

## 9. Out of Scope

- Individual insurer financial data
- Auto insurance or life insurance segments (Phase 1)
- Real time data pipeline
- Proprietary or licensed data sources

---

*"The rate ripple starts at the Bank of Canada. It ends on an insurer's loss statement. This project traces every step in between."*
