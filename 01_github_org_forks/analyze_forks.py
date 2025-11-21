#!/usr/bin/env python3
"""
GitHub Organization Fork Analyzer

This script analyzes all repositories in a GitHub organization and identifies
all external forks (excluding forks by organization members), collecting
detailed information about each fork including:
- Fork creation date
- Fork URL and owner
- Number of commits since forking
- Changes to description and README

Internal forks (by organization members) are automatically filtered out.
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()

class GitHubForkAnalyzer:
    """Analyzes forks across all repositories in a GitHub organization."""

    def __init__(self, token: str):
        """Initialize the analyzer with GitHub token."""
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.org_members = set()  # Cache of organization member usernames

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Make a GitHub API request with rate limit handling."""
        try:
            response = requests.get(url, headers=self.headers, params=params)

            # Check rate limit
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = reset_time - time.time() + 10
                print(f"Rate limit hit. Waiting {wait_time:.0f} seconds...")
                time.sleep(max(wait_time, 0))
                return self._make_request(url, params)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return None

    def _get_paginated_results(self, url: str, params: Optional[Dict] = None) -> List[Dict]:
        """Get all paginated results from a GitHub API endpoint."""
        results = []
        page = 1
        per_page = 100

        if params is None:
            params = {}

        while True:
            params['page'] = page
            params['per_page'] = per_page

            data = self._make_request(url, params)
            if data is None or len(data) == 0:
                break

            results.extend(data)

            if len(data) < per_page:
                break

            page += 1

        return results

    def get_org_repos(self, org_name: str) -> List[Dict]:
        """Get all repositories (public and private) for an organization."""
        print(f"Fetching repositories for organization: {org_name}")
        url = f"{self.base_url}/orgs/{org_name}/repos"
        repos = self._get_paginated_results(url, {'type': 'all'})
        print(f"Found {len(repos)} repositories")
        return repos

    def get_org_members(self, org_name: str) -> set:
        """Get all members of an organization and cache them."""
        if self.org_members:  # Already cached
            return self.org_members

        print(f"Fetching organization members for: {org_name}")
        url = f"{self.base_url}/orgs/{org_name}/members"
        members = self._get_paginated_results(url)

        # Extract usernames and store in set for fast lookup
        self.org_members = {member['login'] for member in members}
        print(f"Found {len(self.org_members)} organization members")
        return self.org_members

    def get_repo_forks(self, owner: str, repo_name: str) -> List[Dict]:
        """Get all forks for a specific repository."""
        url = f"{self.base_url}/repos/{owner}/{repo_name}/forks"
        return self._get_paginated_results(url, {'sort': 'newest'})

    def get_readme(self, owner: str, repo_name: str) -> Optional[str]:
        """Get README content for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo_name}/readme"
        data = self._make_request(url)

        if data and 'content' in data:
            import base64
            try:
                return base64.b64decode(data['content']).decode('utf-8')
            except Exception as e:
                print(f"Error decoding README for {owner}/{repo_name}: {e}")
                return None
        return None

    def compare_commits(self, base_owner: str, base_repo: str,
                       fork_owner: str, fork_repo: str) -> Dict[str, int]:
        """
        Compare commits between original repo and fork.
        Returns dict with ahead_by (commits in fork) and behind_by (commits in original).
        """
        try:
            # Get default branches
            base_data = self._make_request(f"{self.base_url}/repos/{base_owner}/{base_repo}")
            fork_data = self._make_request(f"{self.base_url}/repos/{fork_owner}/{fork_repo}")

            if not base_data or not fork_data:
                return {'ahead_by': 0, 'behind_by': 0, 'error': 'Could not fetch repo data'}

            base_branch = base_data.get('default_branch', 'main')
            fork_branch = fork_data.get('default_branch', 'main')

            # Compare the branches
            url = f"{self.base_url}/repos/{base_owner}/{base_repo}/compare/{base_branch}...{fork_owner}:{fork_branch}"
            compare_data = self._make_request(url)

            if compare_data:
                return {
                    'ahead_by': compare_data.get('ahead_by', 0),
                    'behind_by': compare_data.get('behind_by', 0),
                    'total_commits': compare_data.get('total_commits', 0)
                }
        except Exception as e:
            print(f"Error comparing commits: {e}")

        return {'ahead_by': 0, 'behind_by': 0, 'error': 'Comparison failed'}

    def analyze_fork(self, original_repo: Dict, fork: Dict) -> Dict[str, Any]:
        """Analyze a single fork and collect detailed information."""
        fork_owner = fork['owner']['login']
        fork_name = fork['name']
        original_owner = original_repo['owner']['login']
        original_name = original_repo['name']

        print(f"  Analyzing fork: {fork_owner}/{fork_name}")

        # Basic fork information
        fork_info = {
            'original_repo': f"{original_owner}/{original_name}",
            'original_url': original_repo['html_url'],
            'fork_owner': fork_owner,
            'fork_owner_url': f"https://github.com/{fork_owner}",
            'fork_owner_type': fork['owner']['type'],  # User or Organization
            'fork_name': fork_name,
            'fork_url': fork['html_url'],
            'forked_at': fork['created_at'],
            'fork_updated_at': fork['updated_at'],
            'fork_pushed_at': fork.get('pushed_at', 'Never'),
            'fork_stars': fork.get('stargazers_count', 0),
            'fork_watchers': fork.get('watchers_count', 0),
            'fork_open_issues': fork.get('open_issues_count', 0),
        }

        # Compare descriptions
        original_description = original_repo.get('description', '') or ''
        fork_description = fork.get('description', '') or ''
        fork_info['original_description'] = original_description
        fork_info['fork_description'] = fork_description
        fork_info['description_changed'] = original_description != fork_description

        # Compare commits
        commit_comparison = self.compare_commits(
            original_owner, original_name,
            fork_owner, fork_name
        )
        fork_info['commits_ahead'] = commit_comparison.get('ahead_by', 0)
        fork_info['commits_behind'] = commit_comparison.get('behind_by', 0)
        fork_info['total_commits_difference'] = commit_comparison.get('total_commits', 0)

        # Compare READMEs
        original_readme = self.get_readme(original_owner, original_name)
        fork_readme = self.get_readme(fork_owner, fork_name)

        fork_info['original_has_readme'] = original_readme is not None
        fork_info['fork_has_readme'] = fork_readme is not None

        if original_readme and fork_readme:
            fork_info['readme_changed'] = original_readme != fork_readme
            # Calculate rough change percentage
            if len(original_readme) > 0:
                change_ratio = abs(len(fork_readme) - len(original_readme)) / len(original_readme)
                fork_info['readme_change_percentage'] = round(change_ratio * 100, 2)
            else:
                fork_info['readme_change_percentage'] = 0
        elif original_readme and not fork_readme:
            fork_info['readme_changed'] = True
            fork_info['readme_change_percentage'] = 100.0
        elif not original_readme and fork_readme:
            fork_info['readme_changed'] = True
            fork_info['readme_change_percentage'] = 100.0
        else:
            fork_info['readme_changed'] = False
            fork_info['readme_change_percentage'] = 0

        return fork_info

    def analyze_organization(self, org_name: str) -> List[Dict[str, Any]]:
        """Analyze all forks across all repositories in an organization."""
        # First, get all organization members to filter them out
        org_members = self.get_org_members(org_name)

        repos = self.get_org_repos(org_name)
        all_fork_data = []

        for repo in repos:
            repo_name = repo['name']
            repo_owner = repo['owner']['login']

            print(f"\nAnalyzing repository: {repo_owner}/{repo_name}")

            # Get forks for this repository
            forks = self.get_repo_forks(repo_owner, repo_name)

            if not forks:
                print(f"  No forks found")
                continue

            # Filter out forks by organization members (only keep external forks)
            external_forks = [
                fork for fork in forks
                if fork['owner']['login'] not in org_members
            ]

            internal_count = len(forks) - len(external_forks)
            print(f"  Found {len(forks)} total fork(s): {len(external_forks)} external, {internal_count} internal (excluded)")

            if not external_forks:
                print(f"  No external forks to analyze")
                continue

            # Analyze each external fork
            for fork in external_forks:
                fork_data = self.analyze_fork(repo, fork)
                all_fork_data.append(fork_data)

        return all_fork_data

    def export_to_json(self, data: List[Dict[str, Any]], output_file: str):
        """Export fork data to JSON format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nExported data to JSON: {output_file}")

    def export_to_csv(self, data: List[Dict[str, Any]], output_file: str):
        """Export fork data to CSV format."""
        if not data:
            print("No data to export to CSV")
            return

        # Get all unique keys from all dictionaries
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())

        fieldnames = sorted(fieldnames)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        print(f"Exported data to CSV: {output_file}")

    def export_summary(self, data: List[Dict[str, Any]], output_file: str, org_name: str):
        """Export summary statistics to a text file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"GitHub Fork Analysis Summary\n")
            f.write(f"Organization: {org_name}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Total external forks analyzed: {len(data)}\n")
            f.write(f"(Organization member forks excluded)\n\n")

            f.write("Statistics:\n")
            f.write("-" * 60 + "\n")
            f.write(f"Forks with commits ahead: {sum(1 for f in data if f['commits_ahead'] > 0)}\n")
            f.write(f"Forks with description changes: {sum(1 for f in data if f['description_changed'])}\n")
            f.write(f"Forks with README changes: {sum(1 for f in data if f['readme_changed'])}\n\n")

            # Additional statistics
            total_commits_ahead = sum(f['commits_ahead'] for f in data)
            total_stars = sum(f['fork_stars'] for f in data)
            total_open_issues = sum(f['fork_open_issues'] for f in data)

            f.write(f"Total commits ahead across all forks: {total_commits_ahead}\n")
            f.write(f"Total stars across all forks: {total_stars}\n")
            f.write(f"Total open issues across all forks: {total_open_issues}\n\n")

            # Break down by owner type
            user_forks = sum(1 for f in data if f['fork_owner_type'] == 'User')
            org_forks = sum(1 for f in data if f['fork_owner_type'] == 'Organization')

            f.write("Fork Owner Types:\n")
            f.write("-" * 60 + "\n")
            f.write(f"Individual users: {user_forks}\n")
            f.write(f"Organizations: {org_forks}\n\n")

            # Top forks by commits ahead
            if data:
                f.write("Top 10 Forks by Commits Ahead:\n")
                f.write("-" * 60 + "\n")
                sorted_forks = sorted(data, key=lambda x: x['commits_ahead'], reverse=True)[:10]
                for i, fork in enumerate(sorted_forks, 1):
                    f.write(f"{i}. {fork['fork_owner']}/{fork['fork_name']} - {fork['commits_ahead']} commits ahead\n")
                    f.write(f"   URL: {fork['fork_url']}\n")
                f.write("\n")

            f.write("=" * 60 + "\n")

        print(f"Exported summary to TXT: {output_file}")


def main():
    """Main execution function."""
    # Get GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN not found in environment variables")
        print("Please set GITHUB_TOKEN in your .env file")
        return

    # Get organization name from user or environment
    org_name = os.getenv('GITHUB_ORG')
    if not org_name:
        org_name = input("Enter GitHub organization name: ").strip()

    if not org_name:
        print("Error: Organization name is required")
        return

    # Initialize analyzer
    analyzer = GitHubForkAnalyzer(token)

    # Analyze organization
    print(f"\n{'='*60}")
    print(f"Analyzing forks for organization: {org_name}")
    print(f"{'='*60}\n")

    fork_data = analyzer.analyze_organization(org_name)

    if not fork_data:
        print("\nNo external forks found across all repositories")
        print("(Note: Forks by organization members are excluded)")
        return

    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent

    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Export to all formats
    json_file = output_dir / f"fork_analysis_{org_name}_{timestamp}.json"
    csv_file = output_dir / f"fork_analysis_{org_name}_{timestamp}.csv"
    summary_file = output_dir / f"fork_analysis_{org_name}_{timestamp}_summary.txt"

    analyzer.export_to_json(fork_data, str(json_file))
    analyzer.export_to_csv(fork_data, str(csv_file))
    analyzer.export_summary(fork_data, str(summary_file), org_name)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Analysis Complete!")
    print(f"{'='*60}")
    print(f"Total external forks analyzed: {len(fork_data)}")
    print(f"(Organization member forks excluded)")
    print(f"Forks with commits ahead: {sum(1 for f in fork_data if f['commits_ahead'] > 0)}")
    print(f"Forks with description changes: {sum(1 for f in fork_data if f['description_changed'])}")
    print(f"Forks with README changes: {sum(1 for f in fork_data if f['readme_changed'])}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
