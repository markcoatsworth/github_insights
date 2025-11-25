# GitHub Insights

Analytics pipeline to understand your organization's impact through GitHub fork activity. Analyzes what people are actually doing with your code.

## Setup

```bash
pip install requests python-dotenv

# Create .env file
echo "GITHUB_TOKEN=your_token_here" > .env
echo "GITHUB_ORG=your_org_name" >> .env
```

Get a GitHub token with `repo` and `read:org` scopes.

## Usage

Run the pipeline in order:

### 1. Collect Organization Stats
```bash
cd 00_github_org_stats
python github_org_stats.py
```

### 2. Analyze All Forks
```bash
cd 01_github_org_forks
python analyze_forks.py
```

### 3. Filter to Active Forks
```bash
cd 02_github_org_active_forks
python github_org_active_forks.py ../01_github_org_forks/fork_analysis_*.csv
```

### 4. Generate Business Insights
```bash
cd 03_github_org_active_forks_insights
python github_org_active_forks_insights.py ../02_github_org_active_forks/active_forks_*.csv
```

### 5. Create Presentation
```bash
cd 04_github_org_presentation
python generate_presentation.py ../03_github_org_active_forks_insights/fork_insights_executive_*.json
```

## Output

- **CSV/JSON**: Raw data for analysis
- **Executive summaries**: Business-language reports on what organizations are doing with your code
- **HTML dashboards**: Interactive visualizations

## What It Does

Transforms fork counts into actionable intelligence by analyzing actual code changes to understand business intent, new features, and integration patterns.

## Demo

See the `demo/` directory for an anonymized demo presentation. To create your own safe demo files, see `DEMO_WORKFLOW.md`.
