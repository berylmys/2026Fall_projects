# Critique of the original analysis

**Original work:** Federico D.T., *New York City Rats Health Problem* (2023),
<https://github.com/federicodt/nyc-rat-health-problem>, published article
<https://federicodt.github.io/nyc-rat-health-problem/>. Notebook cell numbers
below refer to the notebooks in that repository (0-indexed, as stored in the `.ipynb` JSON).

The original asks a good question: *is NYC's rat problem getting better or
worse?* Its conclusions are: (1) the problem "is getting worse year after
year", (2) complaints used to be concentrated but "now it is more homogeneous",
i.e. rats have spread, and (3) per-capita, Brooklyn is the worst borough.
Each issue below was checked against the original files.

## A. Calculation errors

| # | Issue | Where | Evidence | Effect |
|---|---|---|---|---|
| A1 | **Wrong numerators in the per-capita rate.** Manhattan is divided using the *Bronx* total (40,563) and the Bronx using the *Queens* total (32,878). | `311 calls…ipynb`, cell 36 | Reproduced exactly in `ratsight.original.original_per_capita`; its output matches `csvs/complains_boroughs_and_population.csv` to every decimal (test `test_original_bug_matches_published_csv`). | Manhattan's rate is understated by ~32%. Corrected ranking puts **Manhattan first, not Brooklyn** (H1). |
| A2 | **Mixed census years.** Manhattan, Bronx and Brooklyn use 2020 census populations; Queens (2,230,722) and Staten Island (468,730) use 2010 figures. | same cell | Values compared with NYC DCP census tables (see `data/population_boroughs.csv`). | Queens and Staten Island rates are inflated relative to the others. |
| A3 | **Monthly average divides by 12** although the data cover 13 full years plus Jan-Jun 2023. | cell 87 | `original_monthly_average` vs `metrics.monthly_profile`. | Jan-Jun overstated by ~22%, Jul-Dec by ~8%; the apparent peak month moves from June to **July** once corrected (H3). |
| A4 | **Partial year treated as complete.** 2023 (data end 25 June) appears in the yearly ranking next to full years. | cells 81-83 | `metrics.complete_years` | Makes 2023 look like a big drop. |

## B. Analytical / inferential problems

| # | Issue | Why it matters | What this project does |
|---|---|---|---|
| B1 | **Complaints are treated as rats.** 311 calls measure *reporting*, which depends on awareness, 311 adoption, population and media attention, not only rat numbers. | "Worse every year" may partly reflect more reporting. | Normalize by population; separate the complaint trend from claims about rats; flag remaining confounders (see Limitations). |
| B2 | **No trend test or uncertainty.** "Getting worse year after year" is read off a bar chart of raw counts sorted by size. | A ranking of years is not a trend; 2018-2020 actually fell. | Theil-Sen slope with 95% CI + Mann-Kendall test; baseline-break test for 2021-22 (H2). |
| B3 | **"More homogeneous / spread" is judged by eye** from two heat maps. Heat maps of raw points mainly show where people live. | Unfalsifiable as stated. | Gini coefficient across ZIP codes per year with bootstrap intervals (H4). Result: concentration slightly **increased**, contradicting the claim. |
| B4 | **Repeat complaints are counted as separate events.** One address (2131 Wallace Ave) has 308 complaints. | Inflates "hotspot" lists and trends. | Group complaints at the same address within N days into episodes; sensitivity at 7/30/90 days (H5). |
| B5 | **"Unspecified" community boards ranked as places.** "Unspecified BROOKLYN" is #1 in the community-board ranking. | Missing data presented as a finding. | Treated as missing (13% of records). |
| B6 | **Health claims (bites, leptospirosis, deaths) are not supported by any data in the repo.** | Conclusions go beyond the evidence. | Out of scope for the data; flagged. Possible extension with NYC DOHMH leptospirosis reports. |
| B7 | **Inspections compared to complaints with raw counts**, and every non-"Passed" result (incl. "Bait applied", "Monitoring visit") is labelled "Failed". | Mislabels routine follow-ups as failures. | Planned for the final stage (see README roadmap). |

## C. Data provenance and reproducibility

| # | Issue | Evidence |
|---|---|---|
| C1 | **"Rats Heat Map" is presented as a third data source, but it is the same data.** | `Rat_Sightings.csv` and `Rats__Heat_Map.csv` have the same 220,517 `Unique Key`s (checked by `load.same_records`; also reported in `outputs/summary.md`). Two 95 MB copies are committed to the repo. |
| C2 | **Inspection data are not in the repo** (`Rodent_Inspection.csv`), so that notebook cannot be re-run. | File referenced in `Rodents inspections…ipynb` cell 3 but absent. |
| C3 | **Windows-only paths** (`"NYC Open Databases\Rat_Sightings.csv"`). | Fails on macOS/Linux. |
| C4 | **Hard-coded numbers** copied from earlier outputs (e.g. cell 35 types the borough totals by hand). | Re-running on new data silently keeps old numbers. |
| C5 | **No functions, tests, docstrings or requirements file**; notebooks depend on hidden state (cell 29 uses `df_borough` before it is defined in cell 35). | Not reproducible top-to-bottom. |
