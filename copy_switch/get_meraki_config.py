#!/usr/bin/env python3
"""
pull_meraki_switch_config.py
Download all port-level configuration for a Meraki switch (by serial #)
and save it to <serial>_switch_ports.csv.

Usage:
    export MERAKI_API_KEY='<your dashboard admin API key>'
    python pull_meraki_switch_config.py Q2XX-YYYY-ZZZZ
"""

import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from meraki import DashboardAPI, APIError   # pip install meraki>=1.45.0

def fetch_ports(dashboard: DashboardAPI, serial: str) -> list[dict]:
    """Return a list of dictionaries – one per switch port."""
    # Meraki API returns up to 1000 ports per call; the SDK paginates for you
    return dashboard.switch.getDeviceSwitchPorts(serial)

def fetch_acls(dashboard: DashboardAPI, serial: str) -> dict:
    """
    Return the switch ACLs (Access Control Lists) for the given switch serial.
    """
    return dashboard.switch.getDeviceSwitchRoutingInterfaceAcl(serial)

def csv_dump(data: list[dict], outfile: Path) -> None:
    """Write the list of dictionaries to outfile (UTF-8 CSV)."""
    if not data:
        raise RuntimeError("No ports returned – is the serial correct?")

    # Keep column order predictable: start with the Meraki field order
    fieldnames = list(data[0].keys())
    with outfile.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def main():
    if len(sys.argv) != 2:
        sys.exit("Syntax: python pull_meraki_switch_config.py <switchSerial>")

    serial = sys.argv[1].upper()
    api_key = os.getenv("meraki_api_key") or os.getenv("MERAKI_API_KEY")
    if not api_key:
        sys.exit("Set MERAKI_API_KEY in your environment first")

    dashboard = DashboardAPI(
        api_key,
        base_url="https://api.meraki.com/api/v1",
        output_log=False,
        suppress_logging=True
    )

    try:
        # Optional sanity check – make sure the serial really is a switch
        device = dashboard.devices.getDevice(serial)
        model = device.get("model", "unknown")
        if not model.startswith(("MS", "MG")):   # MS = Meraki Switch
            print(f"Warning: {serial} looks like a {model}, not a switch.")

        ports = fetch_ports(dashboard, serial)
        outfile = Path(f"{serial}_switch_ports.csv")
        csv_dump(ports, outfile)
        print(
            f"✓ Saved {len(ports)} ports to {outfile} "
            f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        )

    except APIError as e:
        sys.exit(f"Meraki API error: {e}")

if __name__ == "__main__":
    main()
