# Meraki Switch Configuration Migration Tools

This repository contains two Python scripts that work together to migrate switch port configurations between Meraki switches.

## Overview

- **`get_meraki_config.py`** - Downloads all port-level configuration from a source Meraki switch and saves it to a CSV file
- **`push_meraki_config.py`** - Reads the CSV file and applies the configuration to a target Meraki switch

## Prerequisites

1. **Python 3.7+** with the following package:
   ```bash
   pip install meraki>=1.45.0
   ```

2. **Meraki Dashboard API Key** - You need a Dashboard Admin API key with write access to the networks containing your switches.

3. **Network Access** - The switches must be accessible via the Meraki Dashboard API.

## Setup

1. Set your Meraki API key as an environment variable:
   ```bash
   # Windows (PowerShell)
   $env:MERAKI_API_KEY = "your_api_key_here"
   
   # Windows (Command Prompt)
   set MERAKI_API_KEY=your_api_key_here
   
   # Linux/macOS
   export MERAKI_API_KEY='your_api_key_here'
   ```

## Usage

### Step 1: Extract Configuration from Source Switch

Use `get_meraki_config.py` to download the port configuration from your source switch:

```bash
python get_meraki_config.py Q3EB-J68S-P5DH
```

**Parameters:**
- `<switchSerial>` - The serial number of the source Meraki switch (e.g., Q3EB-J68S-P5DH)

**Output:**
- Creates a CSV file named `{SERIAL}_switch_ports.csv` containing all port configurations
- Example: `Q3EB-J68S-P5DH_switch_ports.csv`

### Step 2: Apply Configuration to Target Switch

Use `push_meraki_config.py` to apply the configuration to your target switch:

#### Dry Run (Recommended First)
```bash
python push_meraki_config.py --csv Q3EB-J68S-P5DH_switch_ports.csv --target Q2XX-NEWX-XXXX
```

#### Apply Changes
```bash
python push_meraki_config.py --csv Q3EB-J68S-P5DH_switch_ports.csv --target Q2XX-NEWX-XXXX --apply
```

**Parameters:**
- `--csv` - Path to the CSV file created by the get script
- `--target` - Serial number of the destination switch
- `--apply` - Actually apply the changes (omit for dry-run)
- `--claim-network-id` - (Optional) Network ID to claim the switch into before configuration
- `--delay` - (Optional) Seconds to wait between API calls (default: 0.25)

## Configuration Fields Supported

The following switch port settings are supported for migration:

- `name` - Port name/description
- `tags` - Port tags
- `enabled` - Port enabled/disabled state
- `poeEnabled` - Power over Ethernet settings
- `type` - Port type (access/trunk)
- `vlan` - VLAN assignment
- `voiceVlan` - Voice VLAN assignment
- `allowedVlans` - Allowed VLANs for trunk ports
- `isolationEnabled` - Port isolation
- `rstpEnabled` - Rapid Spanning Tree Protocol
- `stpGuard` - STP guard settings
- `linkNegotiation` - Link negotiation settings
- `portScheduleId` - Port schedule ID
- `accessPolicyType` - Access policy type
- `accessPolicyNumber` - Access policy number
- `daiTrusted` - Dynamic ARP Inspection trust
- `poeFallbackEnabled` - PoE fallback settings
- `udld` - UniDirectional Link Detection

## Example Workflow

1. **Extract from source switch:**
   ```bash
   python get_meraki_config.py Q3EB-J68S-P5DH
   ```
   Output: `Q3EB-J68S-P5DH_switch_ports.csv`

2. **Preview changes (dry run):**
   ```bash
   python push_meraki_config.py --csv Q3EB-J68S-P5DH_switch_ports.csv --target Q2AB-CDEF-GHIJ
   ```

3. **Apply configuration:**
   ```bash
   python push_meraki_config.py --csv Q3EB-J68S-P5DH_switch_ports.csv --target Q2AB-CDEF-GHIJ --apply
   ```

## Advanced Usage

### Claiming a Switch to a Network

If your target switch needs to be claimed to a specific network first:

```bash
python push_meraki_config.py \
    --csv Q3EB-J68S-P5DH_switch_ports.csv \
    --target Q2AB-CDEF-GHIJ \
    --claim-network-id L_123456789012345678 \
    --apply
```

### Adjusting API Call Rate

To slow down API calls (useful for large configurations):

```bash
python push_meraki_config.py \
    --csv Q3EB-J68S-P5DH_switch_ports.csv \
    --target Q2AB-CDEF-GHIJ \
    --delay 0.5 \
    --apply
```

## Error Handling

- Both scripts include comprehensive error handling for API failures
- The push script will continue processing remaining ports even if individual ports fail
- All errors are logged with specific port information for troubleshooting

## Security Notes

- Store your API key securely as an environment variable
- Never commit API keys to version control
- Use read-only API keys for the get script when possible
- Ensure you have proper permissions for the target network before pushing changes

## Troubleshooting

### Common Issues

1. **"Set MERAKI_API_KEY in your environment first"**
   - Solution: Set the environment variable as shown in the Setup section

2. **"Device lookup failed"**
   - Solution: Verify the switch serial number and ensure it's accessible via the API

3. **API rate limiting**
   - Solution: Increase the `--delay` parameter value

4. **Permission errors**
   - Solution: Ensure your API key has write access to the target network

### Support

For Meraki API documentation and support, visit:
- [Meraki API Documentation](https://developer.cisco.com/meraki/api-latest/)
- [Meraki Python SDK](https://github.com/meraki/dashboard-api-python)
