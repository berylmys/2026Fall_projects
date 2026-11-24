"""Download NYC 311 rat sightings from NYC Open Data.

    python scripts/download_data.py [--out data/raw/Rat_Sightings_latest.csv]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

EXPORT_URL = (
    "https://data.cityofnewyork.us/api/views/3q43-55fe/rows.csv?accessType=DOWNLOAD"
)


def download(url: str, out: Path, chunk_size: int = 1 << 20) -> Path:
    """Download the file in chunks and create the output folder if needed."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        written = 0
        with open(tmp, "wb") as handle:
            for chunk in resp.iter_content(chunk_size):
                handle.write(chunk)
                written += len(chunk)
                print(f"\r{written / 1e6:,.0f} MB", end="", flush=True)
    tmp.replace(out)
    print(f"\nSaved {out}")
    return out


def main() -> None:
    """Parse arguments and download the export."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/raw/Rat_Sightings_latest.csv")
    args = parser.parse_args()
    download(EXPORT_URL, Path(args.out))


if __name__ == "__main__":
    main()
