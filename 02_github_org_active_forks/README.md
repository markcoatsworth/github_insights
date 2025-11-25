# Active Fork Filter

Filters fork data to find only forks with actual development activity.

## Usage

```bash
python github_org_active_forks.py ../01_github_org_forks/fork_analysis_*.csv
```

## Active Fork Criteria

A fork is "active" if it has:
1. Diverged with commits (`total_commits_difference > 0`)
2. Been updated since creation (`fork_updated_at > forked_at`)

## Output

- `active_forks_{timestamp}.csv` - Filtered fork data
- Console statistics showing percentage active and top forks by commits

No external dependencies required (uses Python stdlib).
