# GitHub Fork Insights Analyzer

Analyzes actual code changes in active forks to infer business intent and strategic direction.

## Usage

```bash
python github_org_active_forks_insights.py ../02_github_org_active_forks/active_forks_*.csv
```

**Default**: Processes first 5 forks. Edit `max_forks=5` in script to analyze more.

## Output

- `fork_insights_executive_{timestamp}.txt` - Business-language executive summaries
- `fork_insights_executive_{timestamp}.json` - Structured analysis data

## What It Analyzes

- File-level changes (infrastructure, APIs, database, security, etc.)
- Business intent (new features, integration, customization, performance)
- Strategic direction (enterprise hardening, production adaptation, modernization)
- Executive summaries in non-technical language

Designed for senior management and business stakeholders.
