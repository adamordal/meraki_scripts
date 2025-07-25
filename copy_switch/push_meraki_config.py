#!/usr/bin/env python3
"""
push_meraki_switch_config.py
-------------------------------------------------------------
Replay a switch-port CSV (exported by pull_meraki_switch_config.py)
onto another Meraki switch so the port-level configuration
is duplicated 1-for-1.

Usage
-----
# 1. Make sure you have write access to the destination network
# 2. Set your API key (same as before)
export MERAKI_API_KEY='<dashboard admin key>'

# 3. Dry-run (show what would be changed)
python push_meraki_switch_config.py \
       --csv Q3EB-J68S-P5DH_switch_ports.csv \
       --target Q2XX-NEWX-XXXX

# 4. Actually push the changes
python push_meraki_switch_config.py \
       --csv Q3EB-J68S-P5DH_switch_ports.csv \
       --target Q2XX-NEWX-XXXX --apply
"""
import ast
import csv
import os
import sys
import time
import argparse
from meraki import DashboardAPI, APIError   # pip install meraki>=1.45.0

# Only parameters accepted by updateDeviceSwitchPort
ALLOWED_FIELDS = {
    "name",
    "tags",
    "enabled",
    "poeEnabled",
    "type",
    "vlan",
    "voiceVlan",
    "allowedVlans",
    "isolationEnabled",
    "rstpEnabled",
    "stpGuard",
    "linkNegotiation",
    "portScheduleId",
    "accessPolicyType",          # optional
    "accessPolicyNumber",        # optional
    "daiTrusted",                # optional
    "poeFallbackEnabled",        # optional
    "udld",                      # optional (dict)
}

def str_to_native(field, value):
    """
    Convert CSV strings back into native Python types
    so the API call receives proper JSON.
    """
    if value in ("", "nan", "NaN", "None"):
        return None
    if field == "tags":
        # Stored as "['tag1', 'tag2']"
        try:
            return ast.literal_eval(value)
        except Exception:
            return [value]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:                           # numeric?
        if "." in value:
            as_float = float(value)
            if as_float.is_integer():
                return int(as_float)
            return as_float
        return int(value)
    except ValueError:
        return value               # leave as string

def build_kwargs(row):
    """Filter/convert a CSV row into kwargs for the API call."""
    kwargs = {}
    for k in ALLOWED_FIELDS:
        if k in row:
            v = str_to_native(k, row[k])
            if v is not None:
                kwargs[k] = v
    return kwargs

def main():
    parser = argparse.ArgumentParser(
        description="Push a CSV of switch-port settings onto a new Meraki switch"
    )
    parser.add_argument("--csv", required=True, help="CSV file created by pull script")
    parser.add_argument(
        "--target", required=True, help="Destination switch serial (e.g. Q2AB-CDEF-GHIJ)"
    )
    parser.add_argument(
        "--claim-network-id",
        help="Optional: networkId to auto-claim the switch into before pushing",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Really send the API calls; omit for a dry-run",
    )
    parser.add_argument("--delay", type=float, default=0.25, help="Seconds between calls")
    args = parser.parse_args()

    api_key = os.getenv("meraki_api_key") or os.getenv("MERAKI_API_KEY")
    if not api_key:
        sys.exit("Set MERAKI_API_KEY in your environment first")

    dash = DashboardAPI(
        api_key,
        base_url="https://api.meraki.com/api/v1",
        output_log=False,
        suppress_logging=True,
    )

    # Optional: claim the device into a specific network first
    if args.claim_network_id:
        try:
            print(f"Claiming {args.target} into network {args.claim_network_id} …")
            dash.networks.claimNetworkDevices(args.claim_network_id, serials=[args.target])
            print("  ↳ claim request accepted (may take a minute to complete).")
        except APIError as e:
            sys.exit(f"Claim failed: {e}")

    # Sanity check – ensure the target serial is reachable
    try:
        device = dash.devices.getDevice(args.target)
        print(f"Target switch model: {device.get('model','unknown')}")
    except APIError as e:
        sys.exit(f"Device lookup failed: {e}")

    # Stream the CSV
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            port_id = row["portId"]
            params = build_kwargs(row)
            # Show what we’re about to send
            print(f"Port {port_id}: {params}")
            if args.apply:
                try:
                    dash.switch.updateDeviceSwitchPort(args.target, port_id, **params)
                    print("  ↳ pushed ✔")
                except APIError as e:
                    print(f"  ↳ ERROR {e}")
                time.sleep(args.delay)

    if not args.apply:
        print("\nDry-run complete – rerun with --apply to make the changes.")

if __name__ == "__main__":
    main()
