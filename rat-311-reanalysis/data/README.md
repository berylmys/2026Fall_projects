# Data

## Files in this folder

| File | Committed? | Source |
|---|---|---|
| `population_boroughs.csv` | yes | U.S. Census 2010 and 2020 borough populations, as published by NYC Department of City Planning: [2010 table PL-P5](https://www.nyc.gov/assets/planning/download/pdf/data-maps/nyc-population/census2010/t_pl_p5_nyc.pdf), [2020 redistricting presentation](https://www.nyc.gov/assets/districting/downloads/pdf/dcp-presentation-5-11-22.pdf) |
| `raw/Rat_Sightings.csv` | **no** (95 MB, git-ignored) | NYC Open Data, [Rat Sightings (3q43-55fe)](https://data.cityofnewyork.us/Social-Services/Rat-Sightings/3q43-55fe), 311 service requests |

## Getting the raw 311 data

**Option A: same snapshot as the original project (2010 to 25 June 2023).**
Copy `NYC Open Databases/Rat_Sightings.csv` (and optionally `Rats__Heat_Map.csv`)
from <https://github.com/federicodt/nyc-rat-health-problem> into `data/raw/`.
All example outputs in `outputs/` were produced from this snapshot.

**Option B: latest data.** Run

```bash
python scripts/download_data.py
```

This downloads the full current export into `data/raw/Rat_Sightings_latest.csv`.
Point `sightings_csv` in `config.yaml` at that file to re-run every experiment on
newer years.

Do not open the 95 MB file in Excel. The code reads only 11 of the 38 columns,
so it loads in a few seconds with pandas.
