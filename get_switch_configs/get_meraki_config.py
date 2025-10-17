#!/usr/bin/env python3
"""
get_meraki_config.py
Export Meraki MS switch port configuration for every switch in a network.
Writes per-device CSVs, optionally a combined CSV for the network, optional
per-switch Layer 3 data (SVIs and static routes), and optional network-level OSPF.

Quick start:
    # Set your Dashboard API key (either env var name is accepted)
    export MERAKI_API_KEY='<your dashboard admin API key>'
    # PowerShell: $env:MERAKI_API_KEY = '<your dashboard admin API key>'

Usage:
    # Identify the target network using ONE of the following forms
    python get_meraki_config.py --network-id N_123456789012345678 [--combined] [--out-dir PATH] [--l3] [--ospf]
    python get_meraki_config.py --network-url "https://dashboard.meraki.com/.../n/N_123.../..." [--combined] [--out-dir PATH] [--l3] [--ospf]
    python get_meraki_config.py --network-name "HQ Network" --org-id 123456 [--combined] [--out-dir PATH] [--l3] [--ospf]

Flags:
    --network-id       Meraki Network ID (canonical, starts with N_)
    --network-url      Dashboard URL that contains /n/N_... for the target network
    --network-name     Network name (use with --org-id)
    --org-id           Organization ID (required with --network-name)
    --combined         Also write a combined CSV for all switches
    --out-dir PATH     Directory to write CSVs and JSON (default: current directory)
    --l3               Also export per-switch Layer 3 interfaces (SVIs) and static routes
    --ospf             Also export network-level OSPF routing config (JSON)

Outputs:
    <SERIAL>_switch_ports.csv
    <NETWORK_ID>_switch_ports_combined.csv        (when --combined)
    <SERIAL>_l3_interfaces.csv                    (when --l3)
    <SERIAL>_static_routes.csv                    (when --l3)
    <NETWORK_ID>_ospf.json                        (when --ospf)
"""

import csv
import json
import os
import sys
import argparse
from urllib.parse import urlsplit
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

def fetch_l3_interfaces(dashboard: DashboardAPI, serial: str) -> list[dict]:
    """Return L3 interfaces configured on the switch (SVIs)."""
    # Endpoint: GET /devices/{serial}/switch/routing/interfaces
    # SDK: dashboard.switch.getDeviceSwitchRoutingInterfaces(serial)
    return dashboard.switch.getDeviceSwitchRoutingInterfaces(serial)

def fetch_l3_static_routes(dashboard: DashboardAPI, serial: str) -> list[dict]:
    """Return static routes configured on the switch."""
    # Endpoint: GET /devices/{serial}/switch/routing/staticRoutes
    # SDK: dashboard.switch.getDeviceSwitchRoutingStaticRoutes(serial)
    return dashboard.switch.getDeviceSwitchRoutingStaticRoutes(serial)

def fetch_network_ospf(dashboard: DashboardAPI, network_id: str) -> dict:
    """Return network-level OSPF configuration for MS switches in the network."""
    # Endpoint: GET /networks/{networkId}/switch/routing/ospf
    # SDK: dashboard.switch.getNetworkSwitchRoutingOspf(network_id)
    return dashboard.switch.getNetworkSwitchRoutingOspf(network_id)

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

def csv_dump_generic(rows: list[dict], outfile: Path) -> None:
    """Write a list of dicts to CSV inferring headers as union of keys across rows."""
    if not rows:
        # Create an empty file with just headers is ambiguous; skip creating
        return
    headers: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                headers.append(k)
    with outfile.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

def list_network_switches(dashboard: DashboardAPI, network_id: str) -> list[dict]:
    """Return devices in the network that appear to be switches (model starts with MS)."""
    devices = dashboard.networks.getNetworkDevices(network_id)
    switches = [d for d in devices if str(d.get("model", "")).upper().startswith("MS")]
    return switches


def build_combined_rows(serial: str, ports: list[dict]) -> list[dict]:
    """Enrich each port row with the device serial for combined CSV output."""
    rows = []
    for p in ports:
        r = {**p}
        # Ensure serial column is present in combined view
        r.setdefault("deviceSerial", serial)
        rows.append(r)
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export Meraki switch port configs for all switches in a network")
    p.add_argument("--network-id", help="Meraki Network ID (N_...)")
    p.add_argument("--network-url", help="Dashboard URL that contains /n/N_... for the target network")
    p.add_argument("--network-name", help="Network name (use with --org-id)")
    p.add_argument("--combined", action="store_true", help="Also write a combined CSV for all switches")
    p.add_argument("--out-dir", default=".", help="Directory to write CSVs (default: current)")
    p.add_argument("--org-id", help="Optional organization ID for scoping (required with --network-name)")
    p.add_argument("--l3", action="store_true", help="Also export L3 interfaces and static routes per switch")
    p.add_argument("--ospf", action="store_true", help="Also export network-level OSPF config (JSON)")
    return p.parse_args()


def _parse_network_id_from_url(url: str) -> str | None:
    """Extract the network identifier that follows '/n/' in a Dashboard URL."""
    try:
        parts = urlsplit(url)
        segments = [s for s in parts.path.split('/') if s]
        if 'n' in segments:
            idx = segments.index('n')
            if idx + 1 < len(segments):
                return segments[idx + 1]
    except Exception:
        return None
    return None


def resolve_network_id(dashboard: DashboardAPI, args: argparse.Namespace) -> str:
    """Resolve the canonical N_ network ID from various inputs.

    Accepts one of:
    - --network-id N_...
    - --network-url (must contain /n/N_...)
    - --network-name (requires --org-id)
    """
    # Direct N_ network ID
    if args.network_id:
        if args.network_id.startswith("N_"):
            return args.network_id

    # Parse from Dashboard URL
    if getattr(args, 'network_url', None):
        nid = _parse_network_id_from_url(args.network_url)
        if nid and nid.startswith("N_"):
            return nid
        elif nid:
            raise SystemExit(
                f"The URL appears to contain a short network ID '{nid}', which cannot be resolved via API. "
                "Please provide a URL that contains the canonical N_... ID (e.g., /n/N_.../), or provide --network-name with --org-id."
            )
        else:
            raise SystemExit("Could not parse a network identifier from --network-url. Ensure it contains '/n/N_...'.")

    # Lookup by name within an organization
    if getattr(args, 'network_name', None):
        if not args.org_id:
            raise SystemExit("--network-name requires --org-id to disambiguate")
        networks = dashboard.organizations.getOrganizationNetworks(args.org_id, total_pages='all')
        wanted = args.network_name.strip().lower()
        matches = [n for n in networks if str(n.get('name', '')).strip().lower() == wanted]
        if not matches:
            raise SystemExit(f"No network named '{args.network_name}' found in org {args.org_id}.")
        if len(matches) > 1:
            ids = ", ".join(n.get('id') for n in matches if n.get('id'))
            raise SystemExit(
                f"Multiple networks named '{args.network_name}' found in org {args.org_id}: {ids}. Please specify --network-id."
            )
        return matches[0]['id']

    # If a non-canonical ID was provided
    if args.network_id:
        raise SystemExit(
            f"--network-id '{args.network_id}' does not look like a canonical N_ ID. "
            "Provide an N_... value, or use --network-name with --org-id, or a --network-url that contains /n/N_.../"
        )

    # Nothing provided
    raise SystemExit("Provide one of: --network-id N_..., --network-url, or --network-name with --org-id")


def main():
    args = parse_args()

    api_key = os.getenv("meraki_api_key") or os.getenv("MERAKI_API_KEY")
    if not api_key:
        sys.exit("Set MERAKI_API_KEY in your environment first")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    dashboard = DashboardAPI(
        api_key,
        base_url="https://api.meraki.com/api/v1",
        output_log=False,
        suppress_logging=True
    )

    try:
        # Resolve network ID (accept N_, URL, or name+org)
        network_id = resolve_network_id(dashboard, args)

        # Enumerate switches in the network
        switches = list_network_switches(dashboard, network_id)
        if not switches:
            sys.exit(f"No switches found in network {network_id}")

        print(f"Found {len(switches)} switches in network {network_id}")

        combined_rows: list[dict] = []

        for dev in switches:
            serial = dev.get("serial", "").upper()
            model = dev.get("model", "unknown")
            name = dev.get("name") or dev.get("mac") or serial

            # Fetch ports for each switch
            ports = fetch_ports(dashboard, serial)
            outfile = out_dir / f"{serial}_switch_ports.csv"
            csv_dump(ports, outfile)
            print(f"✓ {name} ({model}) – saved {len(ports)} ports to {outfile.name}")

            if args.combined:
                combined_rows.extend(build_combined_rows(serial, ports))

            if args.l3:
                # L3 interfaces (SVIs)
                try:
                    l3_intfs = fetch_l3_interfaces(dashboard, serial)
                except APIError as e:
                    l3_intfs = []
                    print(f"  ! Skipping L3 interfaces on {serial}: {e}")
                if l3_intfs:
                    l3_intf_file = out_dir / f"{serial}_l3_interfaces.csv"
                    csv_dump_generic(l3_intfs, l3_intf_file)
                    print(f"  ✓ Saved {len(l3_intfs)} L3 interfaces to {l3_intf_file.name}")

                # Static routes
                try:
                    static_routes = fetch_l3_static_routes(dashboard, serial)
                except APIError as e:
                    static_routes = []
                    print(f"  ! Skipping static routes on {serial}: {e}")
                if static_routes:
                    sr_file = out_dir / f"{serial}_static_routes.csv"
                    csv_dump_generic(static_routes, sr_file)
                    print(f"  ✓ Saved {len(static_routes)} static routes to {sr_file.name}")

        if args.combined and combined_rows:
            # Build combined fieldnames as a union across rows while keeping a stable order
            # Start from first row keys, append any new keys encountered
            field_order = []
            seen = set()
            for row in combined_rows:
                for k in row.keys():
                    if k not in seen:
                        seen.add(k)
                        field_order.append(k)

            combined_file = out_dir / f"{network_id}_switch_ports_combined.csv"
            with combined_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=field_order)
                writer.writeheader()
                writer.writerows(combined_rows)
            print(f"✓ Wrote combined CSV: {combined_file.name}")

        # OSPF at the network level
        if args.ospf:
            try:
                ospf = fetch_network_ospf(dashboard, network_id)
                ospf_file = out_dir / f"{network_id}_ospf.json"
                with ospf_file.open("w", encoding="utf-8") as f:
                    json.dump(ospf, f, indent=2)
                print(f"✓ Wrote OSPF config: {ospf_file.name}")
            except APIError as e:
                print(f"! OSPF fetch failed: {e}")

        print(f"Done ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    except APIError as e:
        sys.exit(f"Meraki API error: {e}")

if __name__ == "__main__":
    main()
