#!/usr/bin/env python3
"""
GitHub Active Fork Filter

This script filters fork analysis data to identify only "active" forks - those
that have been meaningfully used by the forking party.

Active fork criteria:
- total_commits_difference > 0 (fork has diverged from original with commits)
- fork_updated_at is later than forked_at (fork has been updated since creation)

Usage:
    python github_org_active_forks.py <input_csv_file>
"""

import sys
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict


def parse_datetime(date_string: str) -> datetime:
    """
    Parse GitHub's ISO 8601 datetime format.
    Handles both 'Z' and 'Never' values.
    """
    if date_string == 'Never' or not date_string:
        return datetime.min

    # Remove 'Z' suffix and parse
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return datetime.min


def is_active_fork(row: Dict[str, str]) -> bool:
    """
    Determine if a fork is "active" based on criteria:
    1. Has commits that differ from original (total_commits_difference > 0)
    2. Has been updated since it was created (fork_updated_at > forked_at)
    """
    try:
        # Check total_commits_difference
        total_commits = int(row.get('total_commits_difference', 0))
        if total_commits <= 0:
            return False

        # Check if fork has been updated since creation
        forked_at = parse_datetime(row.get('forked_at', ''))
        updated_at = parse_datetime(row.get('fork_updated_at', ''))

        if updated_at <= forked_at:
            return False

        return True
    except (ValueError, TypeError) as e:
        print(f"Warning: Error processing row for {row.get('fork_owner', 'unknown')}/{row.get('fork_name', 'unknown')}: {e}")
        return False


def filter_active_forks(input_file: str) -> List[Dict[str, str]]:
    """
    Read CSV file and filter to only active forks.
    """
    active_forks = []
    total_count = 0

    print(f"Reading fork data from: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_count += 1
            if is_active_fork(row):
                active_forks.append(row)

    print(f"\nProcessed {total_count} total forks")
    print(f"Found {len(active_forks)} active forks ({len(active_forks)/total_count*100:.1f}%)")

    return active_forks


def export_to_csv(data: List[Dict[str, str]], output_file: str):
    """
    Export filtered fork data to CSV.
    """
    if not data:
        print("No active forks to export")
        return

    fieldnames = data[0].keys()

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Exported active forks to: {output_file}")


def print_statistics(active_forks: List[Dict[str, str]]):
    """
    Print statistics about the active forks.
    """
    if not active_forks:
        return

    print(f"\n{'='*60}")
    print("Active Fork Statistics")
    print(f"{'='*60}")

    # Calculate statistics
    total_commits_ahead = sum(int(f.get('commits_ahead', 0)) for f in active_forks)
    avg_commits_ahead = total_commits_ahead / len(active_forks) if active_forks else 0

    forks_with_desc_changes = sum(1 for f in active_forks if f.get('description_changed', '').lower() == 'true')
    forks_with_readme_changes = sum(1 for f in active_forks if f.get('readme_changed', '').lower() == 'true')

    user_forks = sum(1 for f in active_forks if f.get('fork_owner_type', '') == 'User')
    org_forks = sum(1 for f in active_forks if f.get('fork_owner_type', '') == 'Organization')

    print(f"Total active forks: {len(active_forks)}")
    print(f"Average commits ahead: {avg_commits_ahead:.1f}")
    print(f"Forks with description changes: {forks_with_desc_changes}")
    print(f"Forks with README changes: {forks_with_readme_changes}")
    print(f"\nBreakdown by owner type:")
    print(f"  Individual users: {user_forks}")
    print(f"  Organizations: {org_forks}")

    # Top 5 most active forks
    sorted_forks = sorted(active_forks, key=lambda x: int(x.get('commits_ahead', 0)), reverse=True)[:5]

    print(f"\nTop 5 Most Active Forks (by commits ahead):")
    print("-" * 60)
    for i, fork in enumerate(sorted_forks, 1):
        print(f"{i}. {fork['fork_owner']}/{fork['fork_name']}")
        print(f"   Commits ahead: {fork.get('commits_ahead', 0)}")
        print(f"   URL: {fork.get('fork_url', 'N/A')}")

    print(f"{'='*60}\n")


def main():
    """
    Main execution function.
    """
    if len(sys.argv) != 2:
        print("Usage: python github_org_active_forks.py <input_csv_file>")
        print("\nExample:")
        print("  python github_org_active_forks.py ../01_github_org_forks/fork_analysis_myorg_20251121_104530.csv")
        sys.exit(1)

    input_file = sys.argv[1]

    # Check if input file exists
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    # Filter to active forks
    active_forks = filter_active_forks(input_file)

    if not active_forks:
        print("\nNo active forks found matching the criteria:")
        print("  - total_commits_difference > 0")
        print("  - fork_updated_at > forked_at")
        return

    # Generate output filename
    input_path = Path(input_file)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(__file__).parent / f"active_forks_{timestamp}.csv"

    # Export filtered data
    export_to_csv(active_forks, str(output_file))

    # Print statistics
    print_statistics(active_forks)


if __name__ == "__main__":
    main()
