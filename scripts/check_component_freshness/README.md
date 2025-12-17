# Component Freshness Checker

Scan `metadata.yaml` files and categorize components by their `lastVerified` age.

## Categories

| Status     | Age          | Description                |
|------------|--------------|----------------------------|
| 🟢 Fresh   | < 270 days   | Recently verified          |
| 🟡 Warning | 270-360 days | Should be re-verified soon |
| 🔴 Stale   | > 360 days   | Needs immediate attention  |

## Usage

```bash
# Scan current directory
uv run scripts/check_component_freshness/check_component_freshness.py

# Scan specific path
uv run scripts/check_component_freshness/check_component_freshness.py /path/to/repo

# Export JSON
uv run scripts/check_component_freshness/check_component_freshness.py . --json results.json

# Save report to file
uv run scripts/check_component_freshness/check_component_freshness.py . -o report.txt
```

## Exit Codes

- `0` - No stale components
- `1` - Stale components found

## Example Output

```bash
🟢 Fresh: 5  🟡 Warning: 3  🔴 Stale: 2

🔴 old-component                             400d  components/old
🟡 warning-component                         300d  components/warning
```

## Running Tests

```bash
uv run --with pytest pytest scripts/check_component_freshness/test_check_component_freshness.py -v
```
