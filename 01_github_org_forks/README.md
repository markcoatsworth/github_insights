# GitHub Organization Fork Analyzer

This tool analyzes all repositories in a GitHub organization and identifies detailed information about every fork.

It was created using Claude Code with the following prompt:

```
In the 01_github_org_forks folder, write a python script which leverages the Github API to look over every repo (both public and private) and identifies every fork for each repo. For each fork, give me detailed information about that fork: when it was forked, the new URL, organization, how many commits since it was forked, and any changes to the basic project description or README. Export this data in a relational format (csv or json).
```

## Features

- Scans all repositories (public and private) in an organization
- Identifies all forks for each repository
- Collects detailed fork information:
  - Fork creation date and last update
  - Fork URL and owner (user or organization)
  - Number of commits ahead/behind the original
  - Changes to repository description
  - Changes to README file (with change percentage)
  - Stars, watchers, and open issues count
- Exports data to both CSV and JSON formats

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Configure your GitHub token in the `.env` file in the project root:

```
GITHUB_TOKEN=your_github_token_here
GITHUB_ORG=your_organization_name (optional)
```

**Note:** The token needs appropriate permissions:
- `repo` scope for accessing private repositories
- `read:org` scope for organization access

## Usage

Run the script:

```bash
python analyze_forks.py
```

If `GITHUB_ORG` is not set in `.env`, you'll be prompted to enter the organization name.

## Output

The script generates three files with timestamped filenames:

1. **JSON format**: `fork_analysis_{org_name}_{timestamp}.json`
   - Hierarchical data structure
   - Easy to parse programmatically
   - Contains all collected metadata

2. **CSV format**: `fork_analysis_{org_name}_{timestamp}.csv`
   - Flat tabular format
   - Easy to open in Excel/Google Sheets
   - Suitable for data analysis tools

3. **Summary text file**: `fork_analysis_{org_name}_{timestamp}_summary.txt`
   - Human-readable summary statistics
   - Includes total counts, breakdowns by type
   - Top 10 forks by commits ahead
   - Quick overview without opening full data files

## Output Fields

Each fork entry contains:

| Field | Description |
|-------|-------------|
| `original_repo` | Original repository full name |
| `original_url` | Original repository URL |
| `fork_owner` | Fork owner username/organization |
| `fork_owner_url` | GitHub profile URL of fork owner |
| `fork_owner_type` | Owner type (User or Organization) |
| `fork_name` | Fork repository name |
| `fork_url` | Fork repository URL |
| `forked_at` | Date when fork was created |
| `fork_updated_at` | Last update timestamp |
| `fork_pushed_at` | Last push timestamp |
| `commits_ahead` | Number of commits ahead of original |
| `commits_behind` | Number of commits behind original |
| `total_commits_difference` | Total commit difference |
| `description_changed` | Boolean - if description was modified |
| `original_description` | Original repository description |
| `fork_description` | Fork repository description |
| `readme_changed` | Boolean - if README was modified |
| `readme_change_percentage` | Approximate percentage of README changes |
| `original_has_readme` | Boolean - if original has README |
| `fork_has_readme` | Boolean - if fork has README |
| `fork_stars` | Number of stars on fork |
| `fork_watchers` | Number of watchers on fork |
| `fork_open_issues` | Number of open issues on fork |

## Rate Limiting

The script automatically handles GitHub API rate limiting:
- Monitors rate limit status
- Pauses execution when limit is reached
- Resumes automatically when rate limit resets

## Example Console Output

```
============================================================
Analysis Complete!
============================================================
Total external forks analyzed: 42
(Organization member forks excluded)
Forks with commits ahead: 15
Forks with description changes: 8
Forks with README changes: 12
============================================================
```

## Example Summary File Content

The generated `*_summary.txt` file contains:

```
============================================================
GitHub Fork Analysis Summary
Organization: your-org-name
Analysis Date: 2025-11-21 10:45:30
============================================================

Total external forks analyzed: 42
(Organization member forks excluded)

Statistics:
------------------------------------------------------------
Forks with commits ahead: 15
Forks with description changes: 8
Forks with README changes: 12

Total commits ahead across all forks: 284
Total stars across all forks: 156
Total open issues across all forks: 23

Fork Owner Types:
------------------------------------------------------------
Individual users: 38
Organizations: 4

Top 10 Forks by Commits Ahead:
------------------------------------------------------------
1. user1/repo-fork - 45 commits ahead
   URL: https://github.com/user1/repo-fork
2. user2/repo-fork - 32 commits ahead
   URL: https://github.com/user2/repo-fork
...
============================================================
```

## Requirements

- Python 3.7+
- GitHub Personal Access Token with appropriate permissions
- Internet connection for API access

## Troubleshooting

**"GITHUB_TOKEN not found"**
- Ensure `.env` file exists in the project root
- Verify the token is correctly formatted

**"Rate limit exceeded"**
- The script will automatically wait
- Consider using a token with higher rate limits
- For very large organizations, the analysis may take considerable time

**"403 Forbidden" errors**
- Verify your token has the required scopes
- Check if you have access to the organization's repositories
