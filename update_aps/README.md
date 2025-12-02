# Meraki AP Metadata Updater

Update Meraki device metadata (e.g., device name) in bulk from a CSV file. The script runs in dry‑run mode by default; pass `--apply` to perform real updates.

Script: `update_ap.py`

## What it does
- Reads a CSV containing device rows (serial and desired name)
- Validates and normalizes CSV headers (handles BOM)
- Calls Meraki API `PUT /devices/{serial}` with `{ name: <value> }`
- Uses retries/backoff for transient HTTP errors and `429` rate limits
- Supports TLS verification toggles and request timeouts

## Requirements
- Python 3.9+
- `requests` (standard dependency usually available)
- Meraki Dashboard API key with permission to update devices

## Install
```powershell
# (Optional) create a virtual environment
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# (No extra packages required beyond requests, which ships with many environments)
# If needed:
pip install requests
```

## Authentication
Set your API key in the environment or pass via `--api-key`. The script checks `MERAKI_API_KEY` first, then `meraki_api_key`.

```powershell
$env:MERAKI_API_KEY = "<your_api_key>"
```

## CSV Format
By default, the script expects two headers:
- `Serial-Number` — device serial
- `WAP-Name` — new device name

You can override header names with `--serial-column` and `--name-column`.

## Usage
```powershell
# Dry-run (default): shows actions without calling the API
python .\update_aps\update_ap.py --csv .\WC_AP_Names.csv

# Apply updates (real API calls)
python .\update_aps\update_ap.py --csv .\WC_AP_Names.csv --apply

# Custom header names
python .\update_aps\update_ap.py --csv .\WC_AP_Names.csv --serial-column Serial --name-column Name --apply

# Disable TLS verification (not recommended) and increase timeout
python .\update_aps\update_ap.py --csv .\WC_AP_Names.csv --apply --no-verify --timeout 60

# Provide API key explicitly
python .\update_aps\update_ap.py --csv .\WC_AP_Names.csv --apply --api-key "<your_api_key>"
```

### Options
- `--csv PATH` — Path to CSV file (required)
- `--serial-column NAME` — CSV header for the device serial (default: `Serial-Number`)
- `--name-column NAME` — CSV header for the device name (default: `WAP-Name`)
- `--apply` — Perform updates (omit for dry‑run)
- `--verify` / `--no-verify` — Enable/disable TLS certificate verification (default: verify)
- `--api-key KEY` — Override environment variable with a direct key string
- `--timeout SECONDS` — HTTP request timeout (default: 30)

## Output
- Dry‑run: prints planned updates like `DRY-RUN would update serial=XXXX name='NewName'`
- Apply: prints success `✓ Updated SERIAL -> 'Name'` or error lines with HTTP status/details
- Final summary for apply mode: `Done. Updated=X Failed=Y`

## Troubleshooting
- "Set MERAKI_API_KEY (or pass --api-key)": ensure your key is present in the environment or provided via flag.
- CSV header mismatch: use `--serial-column` / `--name-column` to match your file; the script shows detected headers when errors occur.
- Rate limits (HTTP 429): the script retries with backoff; if still failing, wait and re‑run.
- TLS issues: prefer `--verify` (default). Use `--no-verify` only for controlled environments.

## Notes
- Serial values are upper‑cased before updating for consistency.
- Only empty serial rows are skipped; empty names are allowed (Meraki will accept setting blank names, but consider data hygiene).
