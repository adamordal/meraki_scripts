#!/usr/bin/env python3
"""
sfptest.py
----------
Fetches SFP module inventory across all switches in an organization.
Shows only populated SFP ports with speed and count summaries.

USAGE
=====
export MERAKI_API_KEY="…"                        # or pass --api-key
python sfptest.py --org-id 123456
python sfptest.py --org-id 123456 --base-url https://api.eu.meraki.com/api/v1
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import csv
import time
from datetime import datetime

import requests

DEF_BASE = "https://api.meraki.com/api/v1"


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Get SFP inventory across all switches in an organization")
    p.add_argument("--api-key", "-k", default=os.getenv("MERAKI_API_KEY"),
                   help="Dashboard API key (env MERAKI_API_KEY)")
    p.add_argument("--org-id", required=True, help="Organization ID")
    p.add_argument("--base-url", default=DEF_BASE, help="Override shard base URL")
    p.add_argument("--csv", action="store_true",
                   help="Save results to CSV file")
    p.add_argument("--json", action="store_true",
                   help="Save detailed JSON data")
    return p.parse_args()


def get_switch_sfp_data(serial: str, hdr: dict, base_url: str) -> tuple[list[dict], str, str]:
    """Get SFP data for a single switch"""
    switch_name = serial
    switch_model = "Unknown"
    
    # Get switch info first
    device_url = f"{base_url.rstrip('/')}/devices/{serial}"
    try:
        r = requests.get(device_url, headers=hdr, timeout=30)
        r.raise_for_status()
        device_info = r.json()
        switch_name = device_info.get("name", serial)
        switch_model = device_info.get("model", "Unknown")
    except requests.RequestException:
        pass

    # Get port configuration
    url = f"{base_url.rstrip('/')}/devices/{serial}/switch/ports"
    try:
        r = requests.get(url, headers=hdr, timeout=30)
        r.raise_for_status()
        ports = r.json()
    except requests.RequestException:
        return [], switch_name, switch_model

    # Get port statuses for real-time information
    status_url = f"{base_url.rstrip('/')}/devices/{serial}/switch/ports/statuses"
    try:
        r_status = requests.get(status_url, headers=hdr, timeout=30)
        r_status.raise_for_status()
        port_statuses = r_status.json()
        
        # Create a mapping of portId to status data
        status_map = {status.get("portId"): status for status in port_statuses}
        
        # Merge status data into port configuration data
        for port in ports:
            port_id = port.get("portId")
            if port_id in status_map:
                port.update(status_map[port_id])
    except requests.RequestException:
        pass  # Continue with config data only

    # Filter for SFP ports with modules
    def is_sfp_port(p: dict) -> bool:
        port_id = int(p.get("portId", 0))
        port_type = p.get("type", "")
        poe_enabled = p.get("poeEnabled", True)
        link_capabilities = p.get("linkNegotiationCapabilities", [])
        
        return bool(
            p.get("portModule")
            or p.get("sfpModulePartNumber") 
            or (p.get("module") or {}).get("partNumber")
            or p.get("sfpProductId")
            or "sfp" in str(port_type).lower()
            or "fiber" in str(port_type).lower()
            or port_id >= 49  # Adjust based on switch models
            or (not poe_enabled and port_id > 48)
            or (link_capabilities and 
                len(link_capabilities) <= 3 and 
                any("1 Gigabit full duplex" in cap for cap in link_capabilities) and
                not any("100 Megabit" in cap or "10 Megabit" in cap for cap in link_capabilities))
        )

    def has_sfp_module(p: dict) -> bool:
        return bool(
            p.get("portModule")
            or p.get("sfpModulePartNumber") 
            or (p.get("module") or {}).get("partNumber")
            or p.get("sfpProductId")
            or p.get("status") == "Connected"
            or (p.get("speed") and p.get("speed") != "Auto negotiate")
        )

    sfp_ports = [p for p in ports if is_sfp_port(p)]
    populated_sfp_ports = [p for p in sfp_ports if has_sfp_module(p)]
    
    return populated_sfp_ports, switch_name, switch_model


def main() -> None:
    a = cli()
    if not a.api_key:
        sys.exit("Provide --api-key or set MERAKI_API_KEY")

    hdr = {
        "X-Cisco-Meraki-API-Key": a.api_key,
        "Accept": "application/json",
    }

    # Get all networks in the organization
    print("Fetching networks...")
    networks_url = f"{a.base_url.rstrip('/')}/organizations/{a.org_id}/networks"
    try:
        r = requests.get(networks_url, headers=hdr, timeout=30)
        r.raise_for_status()
        networks = r.json()
    except requests.RequestException as e:
        sys.exit(f"Failed to fetch networks: {e}")

    # Get all switches across all networks
    print("Fetching switches...")
    all_switches = []
    total_devices = 0
    
    for network in networks:
        network_id = network.get("id")
        network_name = network.get("name")
        devices_url = f"{a.base_url.rstrip('/')}/networks/{network_id}/devices"
        try:
            r = requests.get(devices_url, headers=hdr, timeout=30)
            r.raise_for_status()
            devices = r.json()
            total_devices += len(devices)
            
            # Debug: Let's see what device types we're finding
            device_types = {}
            for device in devices:
                product_type = device.get("productType", "unknown")
                device_types[product_type] = device_types.get(product_type, 0) + 1
            
            # Filter for switches - try multiple possible values
            switches = [d for d in devices if d.get("productType") in ["switch", "switches", "appliance"]]
            
            # Also check if model contains switch keywords
            if not switches:
                switches = [d for d in devices if any(keyword in str(d.get("model", "")).lower() 
                           for keyword in ["ms", "switch", "mx"])]
            
            for switch in switches:
                switch["networkName"] = network_name
                switch["networkId"] = network_id
            all_switches.extend(switches)
            
            if devices:
                print(f"  Network '{network_name}': {len(devices)} devices, {len(switches)} switches")
                if device_types:
                    print(f"    Device types: {device_types}")
                    
        except requests.RequestException as e:
            print(f"  Failed to get devices for network {network_name}: {e}")
            continue

    print(f"Found {len(all_switches)} switches across {len(networks)} networks ({total_devices} total devices)")

    # Process each switch for SFP data
    print(f"\nProcessing {len(all_switches)} switches...")
    start_time = time.time()
    
    org_sfp_data = []
    csv_rows = []
    total_sfp_count = 0
    speed_totals = {}
    
    for i, switch in enumerate(all_switches, 1):
        serial = switch.get("serial")
        network_name = switch.get("networkName", "Unknown")
        
        elapsed = time.time() - start_time
        if i > 1:
            avg_time = elapsed / (i - 1)
            remaining = avg_time * (len(all_switches) - i + 1)
            eta = f" (ETA: {remaining/60:.1f}m)"
        else:
            eta = ""
        
        print(f"[{i}/{len(all_switches)}] {serial} in {network_name}{eta}")
        
        populated_sfp_ports, switch_name, switch_model = get_switch_sfp_data(serial, hdr, a.base_url)
        
        if populated_sfp_ports:
            switch_data = {
                "switch": {
                    "serial": serial,
                    "name": switch_name,
                    "model": switch_model,
                    "networkName": network_name,
                    "networkId": switch.get("networkId")
                },
                "sfp_ports": populated_sfp_ports,
                "sfp_count": len(populated_sfp_ports)
            }
            
            # Add to CSV data
            for port in populated_sfp_ports:
                csv_rows.append({
                    "Switch_Serial": serial,
                    "Switch_Name": switch_name,
                    "Switch_Model": switch_model,
                    "Network_Name": network_name,
                    "Port_ID": port.get("portId"),
                    "Speed": port.get("speed", "Unknown"),
                    "Status": port.get("status", "Unknown"),
                    "Module_Type": (port.get("portModule") or 
                                  port.get("sfpModulePartNumber") or 
                                  (port.get("module") or {}).get("partNumber") or 
                                  port.get("sfpProductId") or 
                                  "Unknown Module"),
                    "Is_Uplink": port.get("isUplink", False),
                    "Traffic_Total_Kbps": port.get("trafficInKbps", {}).get("total", 0)
                })
            
            # Count speeds for this switch
            for port in populated_sfp_ports:
                speed = port.get("speed", "Unknown Speed")
                speed_totals[speed] = speed_totals.get(speed, 0) + 1
            
            org_sfp_data.append(switch_data)
            total_sfp_count += len(populated_sfp_ports)
            
            print(f"  → {len(populated_sfp_ports)} SFP modules")

    elapsed_total = time.time() - start_time
    print(f"\nCompleted in {elapsed_total/60:.1f} minutes")

    # Print summary
    print(f"\n=== Organization SFP Inventory ===")
    print(f"Total SFP modules: {total_sfp_count}")
    print(f"Switches with SFP modules: {len(org_sfp_data)}")
    
    if speed_totals:
        print("\nBy Speed:")
        for speed, count in sorted(speed_totals.items()):
            print(f"  {speed}: {count}")

    # Save data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if a.csv and csv_rows:
        csv_filename = f"org_{a.org_id}_sfp_inventory_{timestamp}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["Switch_Serial", "Switch_Name", "Switch_Model", "Network_Name", 
                         "Port_ID", "Speed", "Status", "Module_Type", "Is_Uplink", "Traffic_Total_Kbps"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nCSV saved to {csv_filename}")
    
    if a.json and org_sfp_data:
        json_filename = f"org_{a.org_id}_sfp_inventory_{timestamp}.json"
        with open(json_filename, "w", encoding="utf-8") as fh:
            json.dump(org_sfp_data, fh, indent=2)
        print(f"JSON saved to {json_filename}")


if __name__ == "__main__":
    main()
