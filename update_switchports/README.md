# Switch Port Update Script

A Python script to bulk update switch port names/descriptions on Cisco Meraki switches using a CSV file.

## Overview

This script connects to the Meraki Dashboard API to:
- Read switch port configurations from a CSV file
- Find specified switches in a Meraki network
- Update port names/descriptions on those switches
- Handle API rate limiting automatically

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- Meraki Dashboard API key with write access to the organization
- CSV file with switch and port information

## Configuration

Before running the script, update these variables in the code:

```python
org_name = 'Your Organization Name'  # Replace with your actual org name
net_name = 'Your Network Name'       # Replace with your target network name
```

## Usage

### Setup
```bash
# Set your API key as an environment variable
export MERAKI_API_KEY="your_api_key_here"

# Run the script
python update_switchport.py
```

### Interactive Prompts
The script will prompt you for:
- CSV filename (include the .csv extension)

## CSV File Format

Create a CSV file with the following columns:

| Switch | Port | Description |
|--------|------|-------------|
| Switch-Name-1 | 1 | Server Connection |
| Switch-Name-1 | 2 | Workstation 1 |
| Switch-Name-1 | 24 | Uplink to Core |
| Switch-Name-2 | 1 | Printer |
| Switch-Name-2 | 12 | Conference Room |

### CSV Requirements:
- **Switch**: Exact name of the switch as it appears in Meraki Dashboard
- **Port**: Port number (1, 2, 3, etc.)
- **Description**: New name/description for the port (spaces will be removed)

### Example CSV Content:
```csv
Switch,Port,Description
MS225-01,1,Server Room Rack A
MS225-01,2,Server Room Rack B
MS225-01,24,Uplink to Distribution
MS225-02,1,Reception Desk
MS225-02,2,Conference Room A
MS225-02,12,Wireless AP - Lobby
```

## How It Works

1. **Organization Discovery**: Finds your organization by name
2. **Network Discovery**: Locates the specified network within the org
3. **Device Enumeration**: Gets all devices in the network
4. **CSV Processing**: Reads and parses the CSV file
5. **Switch Matching**: Matches CSV switch names to actual device names
6. **Port Updates**: Updates each port with the new description
7. **Rate Limiting**: Automatically handles API rate limits with retry logic

## API Calls Made

The script makes the following API calls:
- `GET /organizations` - Find organization
- `GET /organizations/{org_id}/networks` - Find network  
- `GET /networks/{network_id}/devices` - Get devices
- `PUT /devices/{serial}/switch/ports/{port}` - Update port (for each port)

## Error Handling

- **Rate Limiting**: Automatically waits and retries when hitting API limits
- **Missing Switches**: Warns if a switch from CSV is not found in network
- **API Errors**: Displays error codes and details for failed updates
- **Invalid Responses**: Handles non-200 response codes gracefully

## Output

The script provides console output showing:
- Found switches and their serial numbers
- Progress of port updates
- Success/failure status for each port update
- Error details for any failed operations

### Example Output:
```
Enter the name of the csv file. Include file extension.:
ports.csv
Found switch: MS225-01 (Q2XX-XXXX-XXXX)
Updating port 1 on MS225-01
Successful update for: Q2XX-XXXX-XXXX port: 1
Updating port 2 on MS225-01
Successful update for: Q2XX-XXXX-XXXX port: 2
Warning: Switch 'MS225-99' not found in network!
```

## Security Notes

- Uses environment variable for API key (secure)
- Disables SSL warnings (modify if needed for your environment)
- API key requires write permissions to switch configurations

## Limitations

- Only updates port names/descriptions (not other port settings)
- Processes one organization and network at a time
- Removes spaces from port descriptions
- Requires exact switch name matches

## Troubleshooting

### Common Issues:

1. **"Organization not found"**: Check `org_name` variable matches exactly
2. **"Network not found"**: Check `net_name` variable matches exactly  
3. **"Switch not found"**: Verify switch names in CSV match Dashboard names exactly
4. **API errors**: Check API key permissions and rate limits

### Tips:
- Use exact switch names as they appear in Meraki Dashboard
- Check that switches are in the specified network
- Ensure API key has write access to switch configurations
- Test with a small CSV file first
