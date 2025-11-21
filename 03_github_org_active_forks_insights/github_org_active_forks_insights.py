#!/usr/bin/env python3
"""
GitHub Active Fork Insights Analyzer

This script performs deep analysis of active forks to understand how they have
evolved from the original repository by examining actual code changes.

Generates executive-level summaries suitable for senior management.

Usage:
    python github_org_active_forks_insights.py <input_csv_file>
"""

import os
import sys
import csv
import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import Counter
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')


class ForkInsightsAnalyzer:
    """Analyzes forks to understand their evolution through code changes."""

    def __init__(self, token: str, max_forks: int = 5):
        """Initialize the analyzer with GitHub token."""
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.max_forks = max_forks

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Make a GitHub API request with rate limit handling."""
        try:
            response = requests.get(url, headers=self.headers, params=params)

            # Check rate limit
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = reset_time - time.time() + 10
                print(f"  Rate limit hit. Waiting {wait_time:.0f} seconds...")
                time.sleep(max(wait_time, 0))
                return self._make_request(url, params)

            if response.status_code == 404:
                print(f"    HTTP 404: Resource not found at {url}")
                return None

            if response.status_code != 200:
                print(f"    HTTP {response.status_code}: {response.reason}")
                print(f"    URL: {url}")
                if response.status_code == 403:
                    print(f"    Response: {response.text[:200]}")
                return None

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"    Request exception for {url}: {e}")
            return None

    def get_comparison(self, base_owner: str, base_repo: str,
                      head_owner: str, head_repo: str) -> Optional[Dict]:
        """
        Get detailed comparison between original and fork repositories.
        This provides the actual code changes.
        """
        # Get default branches for both repos
        print(f"    Getting branch info for {base_owner}/{base_repo}...")
        base_data = self._make_request(f"{self.base_url}/repos/{base_owner}/{base_repo}")

        print(f"    Getting branch info for {head_owner}/{head_repo}...")
        head_data = self._make_request(f"{self.base_url}/repos/{head_owner}/{head_repo}")

        if not base_data:
            print(f"    ERROR: Could not fetch base repo {base_owner}/{base_repo}")
            return None

        if not head_data:
            print(f"    ERROR: Could not fetch head repo {head_owner}/{head_repo}")
            return None

        base_branch = base_data.get('default_branch', 'main')
        head_branch = head_data.get('default_branch', 'main')

        print(f"    Comparing {base_branch}...{head_owner}:{head_branch}")

        # Compare the repositories
        url = f"{self.base_url}/repos/{base_owner}/{base_repo}/compare/{base_branch}...{head_owner}:{head_branch}"
        comparison = self._make_request(url)

        if not comparison:
            print(f"    ERROR: Comparison API call failed")
        else:
            print(f"    Comparison successful")

        return comparison

    def analyze_file_changes(self, comparison: Dict) -> Dict[str, Any]:
        """
        Analyze the actual files changed to understand what's being modified.
        """
        analysis = {
            'total_files_changed': 0,
            'files_by_type': Counter(),
            'change_categories': set(),
            'key_areas': [],
            'technical_changes': [],
            'specific_files_modified': [],  # Track actual filenames
            'new_files_added': [],
            'files_removed': [],
            'major_changes': []  # Files with large changes
        }

        if not comparison or 'files' not in comparison:
            return analysis

        files = comparison['files']
        analysis['total_files_changed'] = len(files)

        # Categorize files and infer intent
        for file_data in files:
            filename = file_data.get('filename', '')
            status = file_data.get('status', '')  # added, removed, modified
            additions = file_data.get('additions', 0)
            deletions = file_data.get('deletions', 0)
            patch = file_data.get('patch', '')

            # Track all modified files
            analysis['specific_files_modified'].append(filename)

            # Track new/removed files
            if status == 'added':
                analysis['new_files_added'].append(filename)
            elif status == 'removed':
                analysis['files_removed'].append(filename)

            # Track major changes with details
            if additions + deletions > 50:
                analysis['major_changes'].append({
                    'file': filename,
                    'status': status,
                    'additions': additions,
                    'deletions': deletions
                })

            # Categorize by file type
            file_ext = Path(filename).suffix.lower()
            if file_ext:
                analysis['files_by_type'][file_ext] += 1

            # Infer purpose from file paths and names
            filename_lower = filename.lower()

            # Infrastructure and configuration
            if any(x in filename_lower for x in ['docker', 'dockerfile', '.yml', '.yaml', 'ci', 'cd', 'deploy']):
                analysis['change_categories'].add('infrastructure')
            if any(x in filename_lower for x in ['config', 'settings', '.env', '.ini', '.conf']):
                analysis['change_categories'].add('configuration')

            # Testing
            if any(x in filename_lower for x in ['test', 'spec', '__test__', '.test.', '.spec.']):
                analysis['change_categories'].add('testing')

            # Documentation
            if any(x in filename_lower for x in ['readme', 'docs/', 'documentation', '.md', 'license']):
                analysis['change_categories'].add('documentation')

            # Security
            if any(x in filename_lower for x in ['auth', 'security', 'crypto', 'password', 'token', 'secret']):
                analysis['change_categories'].add('security')

            # Database
            if any(x in filename_lower for x in ['migration', 'schema', 'model', 'database', 'db/', 'sql']):
                analysis['change_categories'].add('database')

            # API
            if any(x in filename_lower for x in ['api/', 'endpoint', 'route', 'controller', 'handler']):
                analysis['change_categories'].add('api')

            # Frontend/UI
            if any(x in filename_lower for x in ['.css', '.scss', '.html', '.jsx', '.tsx', '.vue', 'component', 'ui/']):
                analysis['change_categories'].add('frontend')

            # Dependencies
            if any(x in filename_lower for x in ['package.json', 'requirements.txt', 'go.mod', 'pom.xml', 'build.gradle', 'gemfile', 'cargo.toml']):
                analysis['change_categories'].add('dependencies')

        # Identify key areas (top file types)
        analysis['key_areas'] = [ext for ext, count in analysis['files_by_type'].most_common(3)]

        return analysis

    def analyze_commit_content(self, comparison: Dict) -> Dict[str, Any]:
        """
        Analyze commit messages to understand development intent.
        Focus on extracting business meaning and specific features/changes.
        """
        analysis = {
            'development_focus': [],
            'key_features_mentioned': [],
            'specific_actions': [],
            'commit_sample': []
        }

        if not comparison or 'commits' not in comparison:
            return analysis

        commits = comparison['commits']

        # Collect commit messages
        all_messages = []
        for commit in commits[:20]:  # Analyze up to 20 most recent commits
            msg = commit.get('commit', {}).get('message', '')
            # Get first line only (the title)
            title = msg.split('\n')[0].strip()
            if title:
                all_messages.append(title)
                analysis['commit_sample'].append(title)

        if not all_messages:
            return analysis

        combined_text = ' '.join(all_messages).lower()

        # Extract specific technical terms and features
        # Look for common patterns like "add X", "implement Y", "support for Z"
        feature_patterns = [
            r'add(?:ed|ing)?\s+(\w+(?:\s+\w+){0,2})',
            r'implement(?:ed|ing)?\s+(\w+(?:\s+\w+){0,2})',
            r'support\s+for\s+(\w+(?:\s+\w+){0,2})',
            r'new\s+(\w+(?:\s+\w+){0,2})',
            r'enable(?:d)?\s+(\w+(?:\s+\w+){0,2})',
            r'integrate(?:d)?\s+(\w+(?:\s+\w+){0,2})'
        ]

        mentioned_features = []
        for pattern in feature_patterns:
            matches = re.findall(pattern, combined_text)
            mentioned_features.extend(matches[:3])  # Limit per pattern

        # Filter out common stop words and very generic terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'tests', 'test'}
        analysis['key_features_mentioned'] = [
            f.strip() for f in mentioned_features[:5]
            if f.strip() and f.strip() not in stop_words and len(f.strip()) > 3
        ]

        # Detect development focus patterns
        patterns = {
            'new_capabilities': ['add support', 'implement', 'introduce', 'new feature', 'enable', 'allow'],
            'improvements': ['improve', 'enhance', 'optimize', 'better', 'upgrade', 'modernize'],
            'bug_fixes': ['fix', 'resolve', 'patch', 'correct', 'repair'],
            'customization': ['customize', 'adapt', 'tailor', 'modify for', 'adjust'],
            'integration': ['integrate', 'connect', 'link', 'bridge', 'compatible'],
            'security': ['security', 'secure', 'vulnerability', 'auth', 'permission'],
            'performance': ['performance', 'faster', 'speed', 'efficiency', 'scale'],
            'refactoring': ['refactor', 'restructure', 'reorganize', 'clean up']
        }

        focus_scores = {}
        for category, keywords in patterns.items():
            score = sum(combined_text.count(keyword) for keyword in keywords)
            if score > 0:
                focus_scores[category] = score

        # Sort by frequency
        sorted_focus = sorted(focus_scores.items(), key=lambda x: x[1], reverse=True)
        analysis['development_focus'] = [cat for cat, score in sorted_focus[:3]]

        return analysis

    def generate_executive_summary(self, fork_data: Dict, file_analysis: Dict,
                                   commit_analysis: Dict, readme_changed: bool) -> str:
        """
        Generate an executive-level summary suitable for senior management.
        Focus on SPECIFIC changes and what they accomplish, not generic categories.
        """
        fork_owner = fork_data['fork_owner']
        original_repo = fork_data['original_repo']
        owner_type = fork_data.get('fork_owner_type', 'User')

        summary_parts = []

        # Opening - Who and what (make it more specific)
        files_changed = file_analysis.get('total_files_changed', 0)
        if owner_type == 'Organization':
            summary_parts.append(f"Organization '{fork_owner}' has developed a customized version of {original_repo} with {files_changed} files modified.")
        else:
            summary_parts.append(f"Developer '{fork_owner}' has created a fork of {original_repo} with {files_changed} file modifications.")

        # SPECIFIC changes - what actually changed
        specific_details = self._extract_specific_changes(file_analysis, commit_analysis)
        if specific_details:
            summary_parts.append(specific_details)

        # Add concrete examples from files or commits
        concrete_example = self._get_concrete_example(file_analysis, commit_analysis)
        if concrete_example:
            summary_parts.append(concrete_example)

        # Business context from description or patterns
        business_context = self._infer_business_context(fork_data, file_analysis, commit_analysis)
        if business_context:
            summary_parts.append(business_context)

        # Strategic significance
        significance = self._assess_significance(file_analysis, commit_analysis, fork_data)
        if significance:
            summary_parts.append(significance)

        # Combine into executive summary (4-5 sentences with actual details)
        summary = ' '.join(summary_parts[:5])
        return summary if summary else "Fork analysis incomplete - insufficient data to generate summary."

    def _extract_specific_changes(self, file_analysis: Dict, commit_analysis: Dict) -> str:
        """Extract specific details about what changed."""
        details = []

        # Look at specific files added
        new_files = file_analysis.get('new_files_added', [])
        if new_files:
            notable_new = [f for f in new_files[:3] if not f.startswith('.')]
            if notable_new:
                file_list = ', '.join([Path(f).name for f in notable_new[:2]])
                details.append(f"new files including {file_list}")

        # Look at features mentioned in commits
        features = commit_analysis.get('key_features_mentioned', [])
        if features and len(features) > 0:
            # Clean up and present features
            feature_str = ', '.join(features[:2])
            details.append(f"work on {feature_str}")

        # Look at major changes
        major_changes = file_analysis.get('major_changes', [])
        if major_changes:
            top_change = major_changes[0]
            file_name = Path(top_change['file']).name
            details.append(f"significant modifications to {file_name}")

        if details:
            return f"The fork includes {' and '.join(details[:3])}."

        # Fallback to categories if no specific details
        categories = file_analysis.get('change_categories', set())
        if categories:
            cat_list = ', '.join(sorted(categories)[:3])
            return f"Modifications span {cat_list} components."

        return ""

    def _get_concrete_example(self, file_analysis: Dict, commit_analysis: Dict) -> str:
        """Provide a concrete example of what was done."""
        # Try to use commit messages for concrete examples
        commit_samples = commit_analysis.get('commit_sample', [])
        if commit_samples and len(commit_samples) > 0:
            # Pick the most descriptive commit (longest, but not too long)
            descriptive = [c for c in commit_samples if 20 < len(c) < 100]
            if descriptive:
                example = descriptive[0]
                # Clean it up for executive presentation
                example = example.capitalize() if example else ""
                if example and not example.endswith('.'):
                    example += '.'
                return f"Recent work includes: \"{example}\""

        # Fallback: describe file type changes
        files_by_type = file_analysis.get('files_by_type', Counter())
        if files_by_type:
            top_types = files_by_type.most_common(2)
            type_desc = ' and '.join([f"{count} {ext} files" for ext, count in top_types])
            return f"Changes primarily affect {type_desc}."

        return ""

    def _infer_business_context(self, fork_data: Dict, file_analysis: Dict,
                                commit_analysis: Dict) -> str:
        """Infer the business context and purpose."""
        categories = file_analysis.get('change_categories', set())
        focus = commit_analysis.get('development_focus', [])

        # Check for custom description
        desc_changed = fork_data.get('description_changed', '').lower() == 'true'
        fork_desc = fork_data.get('fork_description', '').strip()
        if desc_changed and fork_desc and len(fork_desc) > 10:
            return f"The project has been repositioned as: \"{fork_desc}\"."

        # Infrastructure focus
        if 'infrastructure' in categories or 'dependencies' in categories:
            if 'docker' in str(file_analysis.get('specific_files_modified', [])).lower():
                return "This appears to be an effort to containerize and deploy the software in their environment."
            return "The work focuses on adapting deployment and infrastructure for their operational needs."

        # Testing focus
        if 'testing' in categories and len(file_analysis.get('new_files_added', [])) > 2:
            return "Development includes building out testing infrastructure for quality assurance."

        # Security focus
        if 'security' in categories:
            return "Changes emphasize security enhancements, likely for enterprise or compliance requirements."

        # API/Backend development
        if 'api' in categories and 'database' in categories:
            return "Development extends backend functionality with API and data model enhancements."

        # Frontend work
        if 'frontend' in categories:
            return "Work concentrates on user interface improvements and frontend customization."

        # Integration
        if 'integration' in focus:
            return "The modifications enable integration with their existing technology stack."

        return ""

    def _assess_significance(self, file_analysis: Dict, commit_analysis: Dict,
                            fork_data: Dict) -> str:
        """Assess the strategic significance."""
        files_changed = file_analysis.get('total_files_changed', 0)
        major_changes = len(file_analysis.get('major_changes', []))

        if files_changed > 50 and major_changes > 5:
            return "The substantial scope suggests this is a strategic fork intended for production use."
        elif files_changed > 20:
            return "This represents a meaningful investment in adapting the codebase for their needs."
        elif major_changes > 3:
            return "While targeted, the changes show deliberate effort to modify core functionality."

        return ""

    def _infer_business_purpose(self, categories: Set[str], focus: List[str],
                                file_analysis: Dict) -> str:
        """Infer the business purpose from technical changes."""

        # Infrastructure changes suggest deployment/scaling
        if 'infrastructure' in categories and 'dependencies' in categories:
            return "The primary focus appears to be adapting the software for deployment in their specific environment, including infrastructure and dependency modifications."

        # API + database = backend development
        if 'api' in categories and 'database' in categories:
            return "Development efforts center on extending the backend capabilities, with changes to data models and API endpoints."

        # Frontend changes
        if 'frontend' in categories:
            if 'api' in categories:
                return "The fork introduces user-facing features and interface improvements while extending backend functionality."
            return "The work focuses on user interface enhancements and frontend customizations."

        # Security focus
        if 'security' in categories:
            return "Security enhancements and authentication modifications are the primary focus, suggesting enterprise or compliance requirements."

        # Testing additions
        if 'testing' in categories and len(categories) > 2:
            return "The team has invested in quality assurance infrastructure while implementing functional changes."

        # Configuration heavy
        if 'configuration' in categories and len(categories) <= 2:
            return "The modifications primarily involve configuration adjustments to adapt the software for their operational requirements."

        # General development
        if 'new_capabilities' in focus:
            return "The fork extends the original project with new capabilities and features tailored to their specific needs."

        if 'improvements' in focus:
            return "Development efforts focus on improving and enhancing existing functionality rather than adding entirely new features."

        if 'customization' in focus:
            return "The changes represent a customization effort to adapt the software for specific organizational requirements."

        return "The fork includes various modifications to adapt the software for their particular use case."

    def _determine_strategic_direction(self, categories: Set[str], focus: List[str],
                                       fork_data: Dict) -> str:
        """Determine the strategic direction of the fork."""

        # Check if description changed for rebranding
        desc_changed = fork_data.get('description_changed', '').lower() == 'true'
        fork_desc = fork_data.get('fork_description', '').strip()

        # Rebranding/productization
        if desc_changed and fork_desc and len(fork_desc) > 20:
            return f"The project has been repositioned with a new identity: \"{fork_desc[:100]}\"."

        # Performance/scaling focus
        if 'performance' in focus or 'infrastructure' in categories:
            return "The strategic direction emphasizes performance optimization and scalability for production environments."

        # Integration focus
        if 'integration' in focus:
            return "The modifications support integration with other systems or platforms in their technology ecosystem."

        # Enterprise hardening
        if 'security' in categories and 'testing' in categories:
            return "The fork demonstrates an enterprise-hardening strategy with emphasis on security and reliability."

        # Maintenance/modernization
        if 'improvements' in focus and 'dependencies' in categories:
            return "The development strategy focuses on maintaining and modernizing the codebase for continued viability."

        return ""

    def analyze_fork(self, fork_data: Dict) -> Dict[str, Any]:
        """Perform deep analysis of a single fork."""
        fork_owner = fork_data['fork_owner']
        fork_name = fork_data['fork_name']
        original_repo = fork_data['original_repo']
        original_owner, original_name = original_repo.split('/')

        print(f"\n{'='*60}")
        print(f"Analyzing: {fork_owner}/{fork_name}")
        print(f"Original: {original_repo}")
        print(f"{'='*60}")

        insights = {
            'fork_owner': fork_owner,
            'fork_name': fork_name,
            'fork_url': fork_data.get('fork_url', ''),
            'fork_owner_url': fork_data.get('fork_owner_url', ''),
            'original_repo': original_repo,
            'original_url': fork_data.get('original_url', ''),
            'commits_ahead': fork_data.get('commits_ahead', 0)
        }

        # Get detailed comparison between repos
        print("  Fetching code changes...")
        comparison = self.get_comparison(original_owner, original_name, fork_owner, fork_name)

        if not comparison:
            print(f"  ERROR: Could not fetch comparison data")
            insights['summary'] = f"Unable to analyze fork by {fork_owner}. The repository may be private or inaccessible."
            insights['error'] = 'comparison_failed'
            return insights

        # Debug: Show what we got
        files_count = len(comparison.get('files', []))
        commits_count = len(comparison.get('commits', []))
        print(f"  Found {commits_count} commits and {files_count} files changed")

        # Analyze actual file changes
        print("  Analyzing file modifications...")
        file_analysis = self.analyze_file_changes(comparison)
        insights['file_analysis'] = file_analysis

        # Analyze commit content for business intent
        print("  Understanding development intent...")
        commit_analysis = self.analyze_commit_content(comparison)
        insights['commit_analysis'] = commit_analysis

        # Check if README changed
        readme_changed = fork_data.get('readme_changed', '').lower() == 'true'

        # Generate executive summary
        print("  Generating executive summary...")
        summary = self.generate_executive_summary(fork_data, file_analysis,
                                                  commit_analysis, readme_changed)
        insights['summary'] = summary

        print(f"\n  Executive Summary:\n  {summary}\n")

        return insights

    def process_csv(self, input_file: str) -> List[Dict[str, Any]]:
        """Process the CSV file and analyze forks."""
        all_insights = []

        print(f"Reading active forks from: {input_file}")
        print(f"Processing first {self.max_forks} forks...\n")

        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            forks = list(reader)

        if len(forks) == 0:
            print("No forks found in CSV file")
            return []

        # Process only the first N forks
        forks_to_process = forks[:self.max_forks]

        for i, fork_data in enumerate(forks_to_process, 1):
            print(f"\n[{i}/{len(forks_to_process)}]")
            try:
                insights = self.analyze_fork(fork_data)
                all_insights.append(insights)
            except Exception as e:
                print(f"Error analyzing fork: {e}")
                continue

        return all_insights

    def _prepare_for_json(self, data: Any) -> Any:
        """Convert sets and other non-JSON-serializable types for export."""
        if isinstance(data, set):
            return sorted(list(data))
        elif isinstance(data, dict):
            return {key: self._prepare_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._prepare_for_json(item) for item in data]
        else:
            return data

    def export_insights(self, insights: List[Dict[str, Any]], output_file: str):
        """Export insights to JSON and text formats."""
        # Convert sets to lists for JSON serialization
        json_safe_insights = self._prepare_for_json(insights)

        # Export detailed JSON
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_safe_insights, f, indent=2, ensure_ascii=False)
        print(f"\nExported detailed insights to: {json_file}")

        # Export executive report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("GITHUB FORK ANALYSIS - EXECUTIVE REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Report Date: {datetime.now().strftime('%B %d, %Y')}\n")
            f.write(f"Repositories Analyzed: {len(insights)}\n")
            f.write("=" * 80 + "\n\n")

            for i, insight in enumerate(insights, 1):
                f.write(f"{i}. {insight['fork_owner']}/{insight['fork_name']}\n")
                f.write(f"   {'-' * 70}\n")
                f.write(f"   Repository: {insight['fork_url']}\n")
                f.write(f"   Developer/Organization: {insight['fork_owner_url']}\n")
                f.write(f"   Based on: {insight['original_repo']}\n\n")

                f.write(f"   EXECUTIVE SUMMARY:\n")
                f.write(f"   {insight['summary']}\n\n")

                # Add technical context if available
                if 'file_analysis' in insight:
                    file_analysis = insight['file_analysis']
                    categories = file_analysis.get('change_categories', set())
                    if categories:
                        f.write(f"   Technical Areas: {', '.join(sorted(categories))}\n")

                    files_changed = file_analysis.get('total_files_changed', 0)
                    if files_changed > 0:
                        f.write(f"   Scope: {files_changed} files modified\n")

                f.write("\n" + "=" * 80 + "\n\n")

        print(f"Exported executive report to: {output_file}")


def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python github_org_active_forks_insights.py <input_csv_file>")
        print("\nExample:")
        print("  python github_org_active_forks_insights.py ../02_github_org_active_forks/active_forks_20251121_105530.csv")
        sys.exit(1)

    input_file = sys.argv[1]

    # Check if input file exists
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    # Get GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN not found in environment variables")
        print("Please set GITHUB_TOKEN in your .env file")
        sys.exit(1)

    # Initialize analyzer (limit to 5 forks for now)
    analyzer = ForkInsightsAnalyzer(token, max_forks=5)

    # Process forks
    insights = analyzer.process_csv(input_file)

    if not insights:
        print("\nNo insights generated")
        return

    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent
    output_file = output_dir / f"fork_insights_executive_{timestamp}.txt"

    # Export insights
    analyzer.export_insights(insights, str(output_file))

    print(f"\n{'='*80}")
    print(f"Analysis complete! Processed {len(insights)} forks.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
