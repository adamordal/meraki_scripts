#! /usr/bin/env python
"""Update Meraki device metadata (e.g., device name) from a CSV.

Reads a CSV with at least two columns (defaults):
  - Serial-Number
  - WAP-Name

By default, runs in dry-run mode and prints what would be updated. Use --apply to
perform updates. Supports robust CSV parsing, API retries, and configurable TLS verification.
"""
import csv
import json
import time
import os
import argparse
from typing import List, Dict

import requests
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


def build_session(api_key: str, verify_tls: bool = True, timeout: int = 30) -> requests.Session:
    """Create a requests Session with retries and default headers."""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": api_key,
    })

    # Retry on common transient errors and 429 with respect to Retry-After
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("PUT", "GET", "POST"),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    # Stash convenience attrs
    s.verify = verify_tls
    s.request_timeout = timeout

    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return s


def update_device(session: requests.Session, serial: str, name: str) -> tuple[int, dict | str]:
    """Update a device's friendly name. Returns (status_code, response).

    Does a PUT /devices/{serial} with payload {"name": name}.
    """
    url = f"https://api.meraki.com/api/v1/devices/{serial}"
    payload = {"name": name}
    try:
        resp = session.put(url, json=payload, timeout=getattr(session, "request_timeout", 30))
    except requests.RequestException as e:
        return 0, f"request-error: {e}"

    if resp.headers.get("Content-Type", "").startswith("application/json"):
        body: dict | str
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
    else:
        body = resp.text
    return resp.status_code, body


def read_devices_from_csv(
    csv_path: str,
    serial_col: str = "Serial-Number",
    name_col: str = "WAP-Name",
) -> List[Dict[str, str]]:
    """Read devices from CSV and return list of dicts with keys serial, name."""
    devices: List[Dict[str, str]] = []
    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV appears to have no headers")

        # Normalize header names (trim, remove BOM if present)
        headers = [h.strip().lstrip("\ufeff") for h in reader.fieldnames]
        header_map = {orig: norm for orig, norm in zip(reader.fieldnames, headers)}

        # Build index for desired columns (case-sensitive after normalization)
        try:
            # Find actual original header name that matches the normalized desired columns
            serial_key = next(orig for orig, norm in header_map.items() if norm == serial_col)
        except StopIteration:
            raise KeyError(
                f"Missing expected column '{serial_col}'. Found columns: {headers}"
            )
        try:
            name_key = next(orig for orig, norm in header_map.items() if norm == name_col)
        except StopIteration:
            raise KeyError(
                f"Missing expected column '{name_col}'. Found columns: {headers}"
            )

        for row in reader:
            serial = (row.get(serial_key) or "").strip()
            name = (row.get(name_key) or "").strip()
            if not serial:
                # Skip rows without a serial
                continue
            devices.append({"serial": serial, "name": name})

    return devices


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Update Meraki device names from a CSV file")
    p.add_argument("--csv", required=True, help="Path to CSV containing device rows")
    p.add_argument("--serial-column", default="Serial-Number", help="CSV header for device serial (default: Serial-Number)")
    p.add_argument("--name-column", default="WAP-Name", help="CSV header for device name (default: WAP-Name)")
    p.add_argument("--apply", action="store_true", help="Perform API updates (default: dry-run)")
    p.add_argument("--verify", dest="verify", action="store_true", help="Verify TLS certificates (default)")
    p.add_argument("--no-verify", dest="verify", action="store_false", help="Disable TLS verification (not recommended)")
    p.set_defaults(verify=True)
    p.add_argument("--api-key", help="Dashboard API key (overrides MERAKI_API_KEY/meraki_api_key env vars)")
    p.add_argument("--timeout", type=int, default=30, help="HTTP request timeout in seconds (default: 30)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    api_key = (
        args.api_key
        or os.getenv("MERAKI_API_KEY")
        or os.getenv("meraki_api_key")
    )
    if not api_key:
        raise SystemExit("Set MERAKI_API_KEY (or pass --api-key)")

    session = build_session(api_key, verify_tls=args.verify, timeout=args.timeout)

    devices = read_devices_from_csv(
        args.csv,
        serial_col=args.serial_column,
        name_col=args.name_column,
    )

    if not devices:
        print("No device rows found in CSV.")
        return

    print(f"Loaded {len(devices)} device(s) from {args.csv}")
    updates = 0
    failures = 0

    for d in devices:
        serial = d["serial"].upper()
        name = d["name"]
        if not args.apply:
            print(f"DRY-RUN would update serial={serial} name='{name}'")
            continue

        status, body = update_device(session, serial, name)
        if status == 200:
            print(f"✓ Updated {serial} -> '{name}'")
            updates += 1
        elif status == 0:
            print(f"! Request error for {serial}: {body}")
            failures += 1
        elif status == 404:
            print(f"! Not found: {serial}")
            failures += 1
        elif status == 429:
            # If we still hit 429 despite retries, wait briefly and retry a final time
            time.sleep(1)
            status, body = update_device(session, serial, name)
            if status == 200:
                print(f"✓ Updated {serial} -> '{name}' (after 429)")
                updates += 1
            else:
                print(f"! 429 still failing for {serial}: {status} {body}")
                failures += 1
        else:
            print(f"! Failed {serial}: HTTP {status} {body}")
            failures += 1

    if args.apply:
        print(f"Done. Updated={updates} Failed={failures}")
    else:
        print("Dry-run complete. Use --apply to perform updates.")


if __name__ == '__main__':
    main()
