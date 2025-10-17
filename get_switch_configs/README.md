# Meraki Switch Config Exporter

Export all port-level configuration for every Meraki MS switch in a single network and save each device to its own CSV. Optionally create a combined CSV for the whole network and export Layer 3 (SVI) interfaces, static routes, and network-level OSPF config.

Script: `get_meraki_config.py`

## What it does
- Discovers all MS-model devices in a Meraki network
- Exports per-switch port configuration to `<SERIAL>_switch_ports.csv`
- Optionally writes a combined CSV across all switches in the network
- Optionally exports per-switch L3 interfaces and static routes
- Optionally exports the network-level OSPF configuration to JSON

## Requirements
- Python 3.9+ (uses modern type hints like `list[dict]`)
- Meraki Python SDK `meraki >= 1.45.0`
- A Dashboard API key with read access to the organization/network

## Install
```powershell
# (Optional) Create and activate a virtual environment
python -m venv .venv
. .venv/Scripts/Activate.ps1

# Install dependencies
pip install --upgrade meraki
```

```bash
# bash/zsh alternative
python -m venv .venv
source .venv/bin/activate
pip install --upgrade meraki
```

## Authentication
Set your API key in the environment. The script accepts either `MERAKI_API_KEY` or `meraki_api_key` (case-insensitive on Windows).

```powershell
# PowerShell
$env:MERAKI_API_KEY = "<your_api_key>"
```

```bash
# bash/zsh
export MERAKI_API_KEY="<your_api_key>"
```

## Usage
You can identify the target network in one of three ways:
- `--network-id N_...` (canonical network ID)
- `--network-url` containing `/n/N_...` (a Dashboard URL)
- `--network-name` with `--org-id` (exact name match within an organization)

Run `--help` to see options:
```powershell
python .\get_meraki_config.py --help
```

### Common examples
```powershell
# 1) By canonical network ID
python .\get_meraki_config.py --network-id N_123456789012345678

# 2) By Dashboard URL that includes /n/N_...
python .\get_meraki_config.py --network-url "https://dashboard.meraki.com/.../n/N_123456789012345678/overview"

# 3) By network name (requires org ID)
python .\get_meraki_config.py --network-name "HQ Network" --org-id 123456

# Write a combined CSV and choose output directory
python .\get_meraki_config.py --network-id N_123... --combined --out-dir .\exports

# Also export L3 interfaces/static routes per switch
python .\get_meraki_config.py --network-id N_123... --l3

# Also export network-level OSPF config
python .\get_meraki_config.py --network-id N_123... --ospf
```

## Output
Files are written to the directory specified by `--out-dir` (default: current directory).

- Per switch ports: `<SERIAL>_switch_ports.csv`
  - Columns match the Meraki API fields returned by `/devices/{serial}/switch/ports`.
- Combined ports: `<NETWORK_ID>_switch_ports_combined.csv`
  - Union of columns across all devices; includes a `deviceSerial` column.
- L3 interfaces: `<SERIAL>_l3_interfaces.csv` (if `--l3`)
- Static routes: `<SERIAL>_static_routes.csv` (if `--l3`)
- OSPF config: `<NETWORK_ID>_ospf.json` (if `--ospf`)

## Notes
- Network resolution:
  - A canonical `N_...` network ID is required. If your URL contains a short ID (e.g. `/n/7sCxqbw/`), supply a URL that includes `/n/N_.../`, or use `--network-name` with `--org-id`.
- Pagination:
  - The Meraki SDK automatically handles pagination for port lists.
- Permissions:
  - Ensure your API key has access to the organization and target network.

## Troubleshooting
- "Set MERAKI_API_KEY in your environment first"
  - Ensure the `MERAKI_API_KEY` (or `meraki_api_key`) environment variable is set in the current shell.
- "No switches found in network"
  - Verify the network contains MS devices and that your account can see them.
- API errors (rate limits, 4xx/5xx)
  - The script surfaces Meraki API exceptions. Re-run after a short delay or verify inputs/permissions.
- Multiple networks with the same name
  - The script will ask you to provide a canonical `--network-id` if `--network-name` matches more than one network.

## License
This script is provided as-is under your repository's license. Review before use in production.
