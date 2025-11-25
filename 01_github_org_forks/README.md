# GitHub Fork Analyzer

Identifies all forks across organization repositories and collects detailed metadata.

## Usage

```bash
python analyze_forks.py
```

Uses `GITHUB_TOKEN` and `GITHUB_ORG` from `.env` file.

## Output

- `fork_analysis_{org}_{timestamp}.json` - Hierarchical fork data
- `fork_analysis_{org}_{timestamp}.csv` - Flat tabular format
- `fork_analysis_{org}_{timestamp}_summary.txt` - Statistics summary

## Data Collected

- Fork creation and update dates
- Commits ahead/behind original
- Description and README changes
- Owner information (user or organization)
- Stars, watchers, issues

Automatically handles GitHub API rate limiting.
