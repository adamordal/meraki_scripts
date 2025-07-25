# SFP Inventory Script

A Python script to fetch SFP module inventory across all switches in a Cisco Meraki organization.

## Overview

This script connects to the Meraki Dashboard API to:
- Discover all switches across all networks in an organization
- Identify SFP/fiber ports on each switch
- Report only populated SFP ports with their module details
- Provide speed and count summaries
- Export data in CSV and/or JSON formats

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- Meraki Dashboard API key with read access to the organization

## Usage

### Basic Usage
```bash
# Set your API key as an environment variable
export MERAKI_API_KEY="your_api_key_here"

# Run the script
python get_sfps.py --org-id 123456
```

### Command Line Options
```bash
python get_sfps.py --org-id 123456 [OPTIONS]

Options:
  --api-key, -k TEXT    Dashboard API key (or set MERAKI_API_KEY env var)
  --org-id TEXT         Organization ID (required)
  --base-url TEXT       Override shard base URL (default: https://api.meraki.com/api/v1)
  --csv                 Save results to CSV file
  --json                Save detailed JSON data
```

### Output Options
```bash
# Save to CSV file
python get_sfps.py --org-id 123456 --csv

# Save to JSON file  
python get_sfps.py --org-id 123456 --json

# Save both formats
python get_sfps.py --org-id 123456 --csv --json
```

## Output

### Console Output
- Progress information during execution
- Summary of total SFP modules found
- Breakdown by speed/type
- Processing time and ETA

### CSV Output
When using `--csv`, creates a file named `org_{org_id}_sfp_inventory_{timestamp}.csv` with columns:
- Switch_Serial
- Switch_Name  
- Switch_Model
- Network_Name
- Port_ID
- Speed
- Status
- Module_Type
- Is_Uplink
- Traffic_Total_Kbps

### JSON Output
When using `--json`, creates a file named `org_{org_id}_sfp_inventory_{timestamp}.json` with detailed hierarchical data including:
- Switch information (serial, name, model, network)
- Complete port configuration and status data
- SFP module details

## How It Works

1. **Discovery**: Fetches all networks in the organization
2. **Switch Identification**: Finds all switches across networks (supports MS series and other Meraki switches)
3. **Port Analysis**: For each switch:
   - Retrieves port configuration
   - Retrieves real-time port status
   - Identifies SFP/fiber ports (ports ≥49, non-PoE ports, fiber types, etc.)
   - Filters for populated ports only
4. **Data Collection**: Aggregates module information, speeds, and traffic data
5. **Export**: Saves to requested formats with timestamp

## API Calls

The script makes the following API calls:
- `/organizations/{org_id}/networks` - Get all networks
- `/networks/{network_id}/devices` - Get devices per network  
- `/devices/{serial}` - Get switch details
- `/devices/{serial}/switch/ports` - Get port configuration
- `/devices/{serial}/switch/ports/statuses` - Get real-time port status

## Error Handling

- Continues processing if individual switches fail
- Reports failed network/device queries
- Graceful handling of API rate limits and timeouts
- Shows progress and ETA for long-running operations

## Examples

### Find all SFP modules in organization
```bash
python get_sfps.py --org-id 123456
```

### Export to Excel-friendly CSV
```bash
python get_sfps.py --org-id 123456 --csv
```

### Full data export for analysis
```bash
python get_sfps.py --org-id 123456 --csv --json
```

### Use with EU shard
```bash
python get_sfps.py --org-id 123456 --base-url https://api.eu.meraki.com/api/v1
```
