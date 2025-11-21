#!/usr/bin/env python3
"""
GitHub Organization Statistics Collector

This script collects comprehensive statistics for all repositories in a GitHub organization,
including both public and private repos (requires appropriate token permissions).

Usage:
    python github_org_stats.py <organization_name> [--token YOUR_TOKEN] [--format json|csv|both]

Environment Variables:
    GITHUB_TOKEN: Your GitHub personal access token (alternative to --token flag)
"""

import requests
import json
import csv
import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional
import argparse


class GitHubOrgStats:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.session = requests.Session()

        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })
        else:
            print("Warning: No GitHub token provided. Only public repos will be accessible.")
            print("Set GITHUB_TOKEN environment variable or use --token flag for private repos.")

    def get_all_repos(self, org_name: str) -> List[Dict]:
        """Fetch all repositories for the organization (paginated)."""
        repos = []
        page = 1
        per_page = 100

        print(f"Fetching repositories for organization: {org_name}")

        while True:
            url = f"https://api.github.com/orgs/{org_name}/repos"
            params = {
                'per_page': per_page,
                'page': page,
                'type': 'all'  # Get all repos including private ones
            }

            response = self.session.get(url, params=params)

            if response.status_code != 200:
                print(f"Error fetching repos: {response.status_code}")
                print(f"Response: {response.text}")
                sys.exit(1)

            page_repos = response.json()

            if not page_repos:
                break

            repos.extend(page_repos)
            print(f"  Fetched {len(repos)} repositories so far...")
            page += 1

        print(f"Total repositories found: {len(repos)}")
        return repos

    def get_commit_count(self, owner: str, repo: str, default_branch: str) -> int:
        """Get the total number of commits in the repository."""
        try:
            # Try to get commit count from the default branch
            url = f"https://api.github.com/repos/{owner}/{repo}/commits"
            params = {'sha': default_branch, 'per_page': 1}

            response = self.session.get(url, params=params)

            if response.status_code != 200:
                return 0

            # GitHub includes the total count in the Link header
            link_header = response.headers.get('Link', '')

            if 'last' in link_header:
                # Parse the last page number from the Link header
                for part in link_header.split(','):
                    if 'rel="last"' in part:
                        # Use regex to extract just the page number
                        match = re.search(r'[?&]page=(\d+)', part)
                        if match:
                            return int(match.group(1))

            # If there's no Link header, there's at most 1 page of commits
            commits = response.json()
            return len(commits) if commits else 0

        except Exception as e:
            print(f"  Warning: Could not get commit count for {repo}: {e}")
            return 0

    def get_contributors_count(self, owner: str, repo: str) -> int:
        """Get the total number of contributors to the repository."""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
            params = {'per_page': 1, 'anon': 'true'}

            response = self.session.get(url, params=params)

            if response.status_code != 200:
                return 0

            # Parse the Link header for total count
            link_header = response.headers.get('Link', '')

            if 'last' in link_header:
                for part in link_header.split(','):
                    if 'rel="last"' in part:
                        # Use regex to extract just the page number
                        match = re.search(r'[?&]page=(\d+)', part)
                        if match:
                            return int(match.group(1))

            # If no Link header, count the results
            contributors = response.json()
            return len(contributors) if contributors else 0

        except Exception as e:
            print(f"  Warning: Could not get contributors for {repo}: {e}")
            return 0

    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get the languages used in the repository."""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/languages"
            response = self.session.get(url)

            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"  Warning: Could not get languages for {repo}: {e}")
            return {}

    def collect_repo_stats(self, org_name: str) -> List[Dict]:
        """Collect comprehensive statistics for all repos in the organization."""
        repos = self.get_all_repos(org_name)
        stats = []

        print(f"\nCollecting detailed statistics for {len(repos)} repositories...")

        for idx, repo in enumerate(repos, 1):
            repo_name = repo['name']
            owner = repo['owner']['login']

            print(f"[{idx}/{len(repos)}] Processing: {repo_name}")

            # Get additional stats that require separate API calls
            commit_count = self.get_commit_count(owner, repo_name, repo['default_branch'])
            contributors_count = self.get_contributors_count(owner, repo_name)
            languages = self.get_languages(owner, repo_name)

            # Calculate primary language by bytes
            primary_language = repo.get('language', 'Unknown')
            if languages:
                primary_language = max(languages, key=languages.get)

            stat = {
                'name': repo_name,
                'full_name': repo['full_name'],
                'description': repo.get('description', ''),
                'visibility': 'private' if repo['private'] else 'public',
                'created_at': repo['created_at'],
                'updated_at': repo['updated_at'],
                'pushed_at': repo.get('pushed_at', ''),
                'size_kb': repo['size'],
                'stars': repo['stargazers_count'],
                'watchers': repo['watchers_count'],
                'forks': repo['forks_count'],
                'open_issues': repo['open_issues_count'],
                'default_branch': repo['default_branch'],
                'primary_language': primary_language,
                'all_languages': ', '.join(languages.keys()) if languages else '',
                'topics': ', '.join(repo.get('topics', [])),
                'license': repo['license']['name'] if repo.get('license') else 'None',
                'commits': commit_count,
                'contributors': contributors_count,
                'has_wiki': repo['has_wiki'],
                'has_pages': repo['has_pages'],
                'has_downloads': repo['has_downloads'],
                'archived': repo['archived'],
                'disabled': repo['disabled'],
                'url': repo['html_url'],
            }

            stats.append(stat)

        return stats

    def save_to_json(self, stats: List[Dict], filename: str):
        """Save statistics to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\nJSON output saved to: {filename}")

    def save_to_csv(self, stats: List[Dict], filename: str):
        """Save statistics to CSV file."""
        if not stats:
            print("No data to save to CSV")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=stats[0].keys())
            writer.writeheader()
            writer.writerows(stats)
        print(f"CSV output saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Collect comprehensive statistics for a GitHub organization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python github_org_stats.py microsoft
  python github_org_stats.py google --token ghp_xxxxx
  python github_org_stats.py netflix --format json
  GITHUB_TOKEN=ghp_xxxxx python github_org_stats.py facebook
        """
    )

    parser.add_argument('organization', help='GitHub organization name')
    parser.add_argument('--token', help='GitHub personal access token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='both',
                        help='Output format (default: both)')
    parser.add_argument('--output-prefix', default=None,
                        help='Output filename prefix (default: org_stats_<org_name>_<timestamp>)')

    args = parser.parse_args()

    # Initialize collector
    collector = GitHubOrgStats(token=args.token)

    # Collect statistics
    stats = collector.collect_repo_stats(args.organization)

    if not stats:
        print("No statistics collected. Exiting.")
        sys.exit(1)

    # Generate output filename prefix
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix = args.output_prefix or f"org_stats_{args.organization}_{timestamp}"

    # Save to requested format(s)
    if args.format in ['json', 'both']:
        collector.save_to_json(stats, f"{prefix}.json")

    if args.format in ['csv', 'both']:
        collector.save_to_csv(stats, f"{prefix}.csv")

    # Generate summary
    summary_lines = []
    summary_lines.append("="*70)
    summary_lines.append("SUMMARY")
    summary_lines.append("="*70)
    summary_lines.append(f"Organization: {args.organization}")
    summary_lines.append(f"Total repositories: {len(stats)}")
    summary_lines.append(f"Public repos: {sum(1 for s in stats if s['visibility'] == 'public')}")
    summary_lines.append(f"Private repos: {sum(1 for s in stats if s['visibility'] == 'private')}")
    summary_lines.append(f"Total stars: {sum(s['stars'] for s in stats):,}")
    summary_lines.append(f"Total forks: {sum(s['forks'] for s in stats):,}")
    summary_lines.append(f"Total commits: {sum(s['commits'] for s in stats):,}")
    summary_lines.append(f"Archived repos: {sum(1 for s in stats if s['archived'])}")

    # Top repos by stars
    top_starred = sorted(stats, key=lambda x: x['stars'], reverse=True)[:5]
    summary_lines.append(f"\nTop 5 most starred repositories:")
    for i, repo in enumerate(top_starred, 1):
        summary_lines.append(f"  {i}. {repo['name']}: {repo['stars']:,} stars")

    # Top repos by forks
    top_forked = sorted(stats, key=lambda x: x['forks'], reverse=True)[:5]
    summary_lines.append(f"\nTop 5 most forked repositories:")
    for i, repo in enumerate(top_forked, 1):
        summary_lines.append(f"  {i}. {repo['name']}: {repo['forks']:,} forks")

    # Language distribution
    languages = {}
    for stat in stats:
        lang = stat['primary_language']
        if lang and lang != 'Unknown':
            languages[lang] = languages.get(lang, 0) + 1

    if languages:
        summary_lines.append(f"\nTop programming languages:")
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary_lines.append(f"  {lang}: {count} repositories")

    summary_lines.append("="*70)

    # Print summary to screen
    print("\n" + "\n".join(summary_lines))

    # Save summary to text file
    summary_file = f"{prefix}_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"GitHub Organization Statistics Summary\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("\n".join(summary_lines))
    print(f"\nSummary saved to: {summary_file}")


if __name__ == '__main__':
    main()
