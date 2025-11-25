# GitHub Organization Statistics

Collects comprehensive stats for all repositories in an organization.

## Usage

```bash
python github_org_stats.py
```

Uses `GITHUB_TOKEN` and `GITHUB_ORG` from `.env` file.

## Output

- `org_stats_{org}_{timestamp}.json` - Full repository data
- `org_stats_{org}_{timestamp}.csv` - Spreadsheet format
- Console summary with top repos and language breakdown
