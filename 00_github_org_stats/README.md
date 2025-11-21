# GitHub Organization Statistics Collector

A Python script to collect comprehensive statistics for all repositories in a GitHub organization, including both public and private repositories.

## Features

Collects the following statistics for each repository:
- Basic info: name, description, visibility (public/private)
- Popularity metrics: stars, watchers, forks
- Activity: creation date, last update, last push
- Code metrics: commits count, contributors/authors count
- Languages: primary language and all languages used
- Size in KB
- Open issues count
- Topics/tags
- License information
- Settings: default branch, wiki, pages, downloads
- Status: archived, disabled
- Direct URL to repository

## Prerequisites

- Python 3.6 or higher
- `requests` library (install via `pip install -r requirements.txt`)
- GitHub Personal Access Token (optional for public repos, required for private repos)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select the following scopes:
     - `repo` (Full control of private repositories) - for private repos
     - `read:org` (Read org and team membership) - for organization access
   - Copy the generated token

## Usage

### Basic usage (public repos only):
```bash
python github_org_stats.py <organization_name>
```

### With authentication token (for private repos):
```bash
python github_org_stats.py <organization_name> --token YOUR_GITHUB_TOKEN
```

### Using environment variable:
```bash
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
python github_org_stats.py <organization_name>
```

### Specify output format:
```bash
# JSON only
python github_org_stats.py <organization_name> --format json

# CSV only
python github_org_stats.py <organization_name> --format csv

# Both (default)
python github_org_stats.py <organization_name> --format both
```

### Custom output filename:
```bash
python github_org_stats.py <organization_name> --output-prefix my_custom_name
```

## Examples

```bash
# Public organization
python github_org_stats.py microsoft

# Private organization with token
python github_org_stats.py my-company --token ghp_xxxxxxxxxxxxx

# Export to JSON only
python github_org_stats.py google --format json

# With environment variable
GITHUB_TOKEN=ghp_xxxxx python github_org_stats.py netflix
```

## Output

The script generates two files (by default):

1. **JSON file**: `org_stats_<org_name>_<timestamp>.json`
   - Structured JSON array with all repository statistics
   - Suitable for programmatic processing

2. **CSV file**: `org_stats_<org_name>_<timestamp>.csv`
   - Spreadsheet-compatible format
   - Easy to open in Excel, Google Sheets, etc.

The script also prints a summary to the console including:
- Total repository count
- Public vs private repo count
- Total stars, forks, and commits
- Top 5 most starred repositories
- Top 5 most forked repositories
- Top programming languages used

## Statistics Collected

| Field | Description |
|-------|-------------|
| name | Repository name |
| full_name | Full repository name (org/repo) |
| description | Repository description |
| visibility | public or private |
| created_at | Creation timestamp |
| updated_at | Last update timestamp |
| pushed_at | Last push timestamp |
| size_kb | Repository size in KB |
| stars | Number of stars |
| watchers | Number of watchers |
| forks | Number of forks |
| open_issues | Number of open issues |
| default_branch | Default branch name |
| primary_language | Primary programming language |
| all_languages | All languages used (comma-separated) |
| topics | Repository topics/tags |
| license | License name |
| commits | Total number of commits |
| contributors | Total number of contributors |
| has_wiki | Wiki enabled |
| has_pages | GitHub Pages enabled |
| has_downloads | Downloads enabled |
| archived | Archived status |
| disabled | Disabled status |
| url | Direct URL to repository |

## Rate Limiting

GitHub API has rate limits:
- Unauthenticated: 60 requests per hour
- Authenticated: 5,000 requests per hour

For large organizations, use an authentication token to avoid rate limiting.

## Troubleshooting

**"No GitHub token provided" warning:**
- This is normal if you're only accessing public repos
- For private repos, provide a token using `--token` flag or `GITHUB_TOKEN` environment variable

**403 Forbidden error:**
- Check that your token has the required scopes (`repo`, `read:org`)
- Verify the token hasn't expired

**Empty results:**
- Verify the organization name is correct
- Check that your token has access to the organization
- For private orgs, ensure you're a member with appropriate permissions

## License

This script is provided as-is for personal and commercial use.
