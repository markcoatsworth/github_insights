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

    def __init__(self, token: str, max_forks: int = None):
        """Initialize the analyzer with GitHub token."""
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.max_forks = max_forks  # None means process all

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

    def get_owner_details(self, owner: str) -> Dict[str, Any]:
        """
        Get detailed information about a repository owner (user or organization).
        Extracts real name, company, bio, location, and other relevant details.
        Also verifies organization and fetches organization homepage.
        """
        print(f"    Fetching owner details for {owner}...")
        url = f"{self.base_url}/users/{owner}"
        data = self._make_request(url)

        details = {
            'owner_login': owner,
            'owner_type': 'Unknown',
            'real_name': None,
            'company': None,
            'organization': None,
            'organization_verified': False,
            'organization_url': None,
            'organization_homepage': None,
            'bio': None,
            'location': None,
            'blog': None,
            'twitter': None,
            'email': None,
            'public_repos': 0,
            'followers': 0
        }

        if not data:
            return details

        # Extract basic info
        details['owner_type'] = data.get('type', 'Unknown')  # User or Organization
        details['real_name'] = data.get('name', '').strip() if data.get('name') else None
        details['bio'] = data.get('bio', '').strip() if data.get('bio') else None
        details['location'] = data.get('location', '').strip() if data.get('location') else None
        details['blog'] = data.get('blog', '').strip() if data.get('blog') else None
        details['twitter'] = data.get('twitter_username', '').strip() if data.get('twitter_username') else None
        details['email'] = data.get('email', '').strip() if data.get('email') else None
        details['public_repos'] = data.get('public_repos', 0)
        details['followers'] = data.get('followers', 0)

        # For organizations, get the homepage directly
        if details['owner_type'] == 'Organization':
            details['organization'] = details['real_name'] or owner
            details['organization_verified'] = True
            details['organization_url'] = f"https://github.com/{owner}"
            if details['blog']:
                details['organization_homepage'] = self._normalize_url(details['blog'])
            print(f"      Organization verified: {details['organization']}")

        # For users, extract and verify company/organization
        else:
            company_raw = data.get('company', '').strip() if data.get('company') else None
            if company_raw:
                # Clean up company name (remove @ if present)
                company_clean = company_raw.lstrip('@').strip()
                details['company'] = company_clean

                # If company starts with @, it's likely a GitHub org - verify it
                if company_raw.startswith('@'):
                    org_verified = self._verify_github_organization(company_clean)
                    if org_verified:
                        details['organization'] = org_verified['name']
                        details['organization_verified'] = True
                        details['organization_url'] = org_verified['url']
                        details['organization_homepage'] = org_verified['homepage']
                        print(f"      Organization verified: {details['organization']}")
                else:
                    details['organization'] = company_clean
                    # Try to find a homepage from the user's blog
                    if details['blog']:
                        details['organization_homepage'] = self._normalize_url(details['blog'])

            # If we still don't have an organization, try to infer from bio or other sources
            if not details['organization']:
                details['organization'] = self._infer_organization(owner, details)

        return details

    def _verify_github_organization(self, org_name: str) -> Optional[Dict[str, str]]:
        """
        Verify if a company name is a valid GitHub organization and get its details.
        Returns organization info including name and homepage.
        """
        print(f"      Verifying GitHub organization: {org_name}")
        url = f"{self.base_url}/orgs/{org_name}"
        data = self._make_request(url)

        if not data:
            print(f"      Organization '{org_name}' not found on GitHub")
            return None

        org_info = {
            'name': data.get('name') or data.get('login'),
            'url': data.get('html_url'),
            'homepage': None
        }

        # Get homepage/blog
        blog = data.get('blog', '').strip() if data.get('blog') else None
        if blog:
            org_info['homepage'] = self._normalize_url(blog)

        return org_info

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL to ensure it has a proper scheme."""
        if not url:
            return None

        url = url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        return url

    def _infer_organization(self, owner: str, details: Dict[str, Any]) -> Optional[str]:
        """
        Try to infer organization from bio, email domain, or other clues.
        """
        org_hints = []

        # Check bio for organization mentions
        bio = details.get('bio', '')
        if bio:
            # Look for patterns like "at Company", "@ Company", "working at Company"
            import re
            patterns = [
                r'(?:at|@)\s+([A-Z][\w\s&]+?)(?:\.|,|\||$)',
                r'(?:working|works)\s+(?:at|for)\s+([A-Z][\w\s&]+?)(?:\.|,|\||$)',
                r'(?:employed|employee)\s+(?:at|of)\s+([A-Z][\w\s&]+?)(?:\.|,|\||$)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, bio)
                if matches:
                    org_hints.extend(matches)

        # Check email domain
        email = details.get('email', '')
        if email and '@' in email:
            domain = email.split('@')[1].lower()
            # Skip generic email providers
            generic_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                             'protonmail.com', 'icloud.com', 'me.com']
            if domain not in generic_domains:
                # Extract company name from domain
                company_name = domain.split('.')[0]
                org_hints.append(company_name.capitalize())

        # Check blog/website domain
        blog = details.get('blog', '')
        if blog and '.' in blog:
            # Extract domain
            domain = blog.replace('http://', '').replace('https://', '').split('/')[0].lower()
            if not any(x in domain for x in ['github.com', 'twitter.com', 'linkedin.com']):
                company_name = domain.split('.')[0]
                org_hints.append(company_name.capitalize())

        # Return the first reasonable hint
        if org_hints:
            return org_hints[0].strip()

        return None

    def get_readme(self, owner: str, repo_name: str) -> Optional[str]:
        """Get README content for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo_name}/readme"
        data = self._make_request(url)

        if data and 'content' in data:
            import base64
            try:
                return base64.b64decode(data['content']).decode('utf-8')
            except Exception as e:
                print(f"    Error decoding README: {e}")
                return None
        return None

    def get_file_content(self, owner: str, repo_name: str, file_path: str) -> Optional[str]:
        """Get content of a specific file from a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo_name}/contents/{file_path}"
        data = self._make_request(url)

        if data and 'content' in data:
            import base64
            try:
                return base64.b64decode(data['content']).decode('utf-8')
            except Exception as e:
                print(f"    Error decoding {file_path}: {e}")
                return None
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

    def analyze_readme_deeply(self, original_readme: Optional[str],
                              fork_readme: Optional[str]) -> Dict[str, Any]:
        """
        Deep NLP analysis of README changes to understand business intent.
        Focus on what was ADDED to understand their purpose.
        """
        analysis = {
            'stated_purpose': None,
            'use_cases': [],
            'target_audience': None,
            'industry_terms': [],
            'problems_solved': [],
            'integrations_mentioned': [],
            'deployment_targets': [],
            'added_sections': [],
            'business_context': None
        }

        if not fork_readme:
            return analysis

        # Get the additions (what's in fork but not in original)
        if original_readme:
            original_lines = set(original_readme.lower().split('\n'))
            fork_lines = fork_readme.split('\n')
            # Lines that are new in the fork
            new_content_lines = [line for line in fork_lines
                                if line.lower().strip() not in original_lines
                                and len(line.strip()) > 10]
            new_content = '\n'.join(new_content_lines)
        else:
            # No original, so everything is new
            new_content = fork_readme

        if not new_content or len(new_content) < 50:
            # Not enough new content to analyze
            return analysis

        new_content_lower = new_content.lower()

        # Extract stated purpose - look for explicit statements
        purpose_patterns = [
            r'(?:this fork|this version|this project|we)\s+(?:is|are)\s+(?:designed|built|created|intended)\s+(?:for|to)\s+([^.!?\n]{10,100})',
            r'(?:purpose|goal|aim):\s*([^.!?\n]{10,100})',
            r'(?:why we forked|reason for fork):\s*([^.!?\n]{10,100})',
            r'(?:optimized|tailored|customized)\s+for\s+([^.!?\n]{10,100})'
        ]

        for pattern in purpose_patterns:
            matches = re.findall(pattern, new_content_lower, re.IGNORECASE)
            if matches:
                analysis['stated_purpose'] = matches[0].strip()
                break

        # Extract use cases
        use_case_patterns = [
            r'use case[s]?:\s*([^#\n]{20,200})',
            r'(?:ideal|perfect|best)\s+for\s+([^.!?\n]{10,100})',
            r'(?:useful|helpful)\s+(?:for|when|if)\s+([^.!?\n]{10,100})',
            r'example[s]?:\s*([^#\n]{20,200})'
        ]

        for pattern in use_case_patterns:
            matches = re.findall(pattern, new_content_lower, re.IGNORECASE)
            analysis['use_cases'].extend([m.strip() for m in matches[:3]])

        # Look for target audience
        audience_patterns = [
            r'(?:for|targeting|aimed at)\s+(enterprises|companies|organizations|teams|developers|researchers|data scientists|ml engineers|healthcare|financial|government)',
            r'(?:enterprise|production|industrial)\s+(?:use|deployment|environment)'
        ]

        for pattern in audience_patterns:
            matches = re.findall(pattern, new_content_lower)
            if matches:
                analysis['target_audience'] = matches[0]
                break

        # Extract industry/domain terms
        industry_keywords = {
            'healthcare': ['patient', 'clinical', 'medical', 'hipaa', 'healthcare', 'hospital', 'diagnosis', 'treatment'],
            'finance': ['trading', 'financial', 'banking', 'payment', 'transaction', 'fraud', 'risk', 'compliance', 'kyc', 'aml'],
            'enterprise': ['enterprise', 'corporate', 'b2b', 'saas', 'multi-tenant', 'sso', 'ldap', 'active directory'],
            'ml/ai': ['machine learning', 'deep learning', 'neural network', 'training', 'inference', 'model serving'],
            'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'containerized', 'microservices'],
            'government': ['government', 'public sector', 'federal', 'compliance', 'air-gapped', 'classified'],
            'education': ['education', 'learning', 'student', 'academic', 'research', 'university'],
            'iot': ['iot', 'sensor', 'edge', 'embedded', 'device', 'hardware']
        }

        detected_industries = []
        for industry, keywords in industry_keywords.items():
            if any(keyword in new_content_lower for keyword in keywords):
                detected_industries.append(industry)

        analysis['industry_terms'] = detected_industries[:3]

        # Extract problems being solved
        problem_patterns = [
            r'(?:solves?|addresses?|fixes?|handles?)\s+(?:the\s+)?(?:problem|issue|challenge)\s+of\s+([^.!?\n]{10,100})',
            r'(?:enables?|allows?|supports?)\s+([^.!?\n]{10,100})',
            r'(?:without|no longer need)\s+([^.!?\n]{10,100})'
        ]

        for pattern in problem_patterns:
            matches = re.findall(pattern, new_content_lower, re.IGNORECASE)
            analysis['problems_solved'].extend([m.strip() for m in matches[:2]])

        # Extract integrations mentioned
        integration_patterns = [
            r'integrat(?:e|es|ion)\s+(?:with\s+)?(\w+(?:\s+\w+)?)',
            r'connect(?:s|ion)?\s+(?:to\s+)?(\w+(?:\s+\w+)?)',
            r'support(?:s)?\s+(\w+(?:\s+\w+)?)\s+(?:integration|api|platform)'
        ]

        integrations = []
        for pattern in integration_patterns:
            matches = re.findall(pattern, new_content_lower)
            integrations.extend([m.strip() for m in matches if len(m.strip()) > 3])

        # Filter out common words
        stop_words = {'the', 'with', 'for', 'and', 'our', 'your', 'this', 'that', 'other'}
        analysis['integrations_mentioned'] = [i for i in integrations[:5] if i not in stop_words]

        # Extract deployment targets
        deployment_keywords = ['aws', 'azure', 'gcp', 'kubernetes', 'k8s', 'docker', 'openshift',
                              'on-premise', 'on-prem', 'cloud', 'hybrid', 'air-gapped', 'offline']
        analysis['deployment_targets'] = [kw for kw in deployment_keywords if kw in new_content_lower]

        # Look for new sections (markdown headers)
        new_sections = re.findall(r'^#{1,3}\s+(.+)$', new_content, re.MULTILINE)
        analysis['added_sections'] = [s.strip() for s in new_sections[:5]]

        # Try to construct business context from all findings
        if analysis['stated_purpose']:
            analysis['business_context'] = f"Explicitly states: {analysis['stated_purpose']}"
        elif analysis['use_cases']:
            analysis['business_context'] = f"Use case: {analysis['use_cases'][0]}"
        elif analysis['industry_terms']:
            industries = ', '.join(analysis['industry_terms'][:2])
            analysis['business_context'] = f"Targeted for {industries} applications"
        elif analysis['problems_solved']:
            analysis['business_context'] = f"Addresses: {analysis['problems_solved'][0]}"

        return analysis

    def analyze_documentation_files(self, fork_owner: str, fork_name: str,
                                   new_doc_files: List[str]) -> Dict[str, Any]:
        """
        Read and analyze new documentation files to understand purpose and intent.
        """
        analysis = {
            'documentation_insights': [],
            'deployment_details': None,
            'architecture_notes': None,
            'integration_details': None,
            'setup_requirements': [],
            'stated_goals': []
        }

        # Focus on documentation files
        doc_file_patterns = {
            'deployment': ['deploy', 'deployment', 'installation', 'setup', 'getting-started', 'quickstart'],
            'architecture': ['architecture', 'design', 'structure'],
            'integration': ['integration', 'api', 'connect'],
            'usage': ['usage', 'guide', 'tutorial', 'examples'],
            'contributing': ['contributing', 'development'],
        }

        # Find relevant doc files
        relevant_docs = []
        for file_path in new_doc_files:
            file_lower = file_path.lower()
            if file_path.endswith('.md') or '/docs/' in file_lower or file_lower.startswith('docs/'):
                relevant_docs.append(file_path)

        print(f"    Found {len(relevant_docs)} new documentation files")

        # Read up to 5 most relevant docs
        for doc_file in relevant_docs[:5]:
            print(f"    Reading: {doc_file}")
            content = self.get_file_content(fork_owner, fork_name, doc_file)

            if not content or len(content) < 100:
                continue

            content_lower = content.lower()
            file_name = Path(doc_file).stem.lower()

            # Extract insights based on file type
            insight = {'file': doc_file, 'type': None, 'key_points': []}

            # Deployment/Setup documentation
            if any(pattern in file_name for pattern in doc_file_patterns['deployment']):
                insight['type'] = 'deployment'

                # Look for deployment targets
                if 'kubernetes' in content_lower or 'k8s' in content_lower:
                    insight['key_points'].append('Kubernetes deployment')
                if 'docker' in content_lower:
                    insight['key_points'].append('Docker containerization')
                if 'aws' in content_lower:
                    insight['key_points'].append('AWS infrastructure')
                if 'azure' in content_lower:
                    insight['key_points'].append('Azure cloud')
                if 'on-premise' in content_lower or 'on-prem' in content_lower:
                    insight['key_points'].append('On-premise deployment')

                # Look for requirements
                req_patterns = [
                    r'(?:requires?|needs?|prerequisites?):\s*([^\n]{10,100})',
                    r'(?:you need|you must have|you should have)\s+([^\n]{10,100})'
                ]
                for pattern in req_patterns:
                    matches = re.findall(pattern, content_lower)
                    analysis['setup_requirements'].extend([m.strip() for m in matches[:3]])

            # Architecture documentation
            elif any(pattern in file_name for pattern in doc_file_patterns['architecture']):
                insight['type'] = 'architecture'

                # Look for architectural patterns
                arch_keywords = ['microservices', 'monolith', 'distributed', 'scalable',
                               'high availability', 'fault tolerant', 'event-driven']
                for keyword in arch_keywords:
                    if keyword in content_lower:
                        insight['key_points'].append(keyword)

            # Integration documentation
            elif any(pattern in file_name for pattern in doc_file_patterns['integration']):
                insight['type'] = 'integration'

                # Look for what they're integrating with
                integration_mentions = re.findall(
                    r'integrat(?:e|ing|ion)\s+(?:with\s+)?([A-Z][\w\s]{3,30})',
                    content
                )
                insight['key_points'].extend([m.strip() for m in integration_mentions[:3]])

            # Extract any explicit goals or purposes
            goal_patterns = [
                r'(?:goal|purpose|objective):\s*([^\n]{15,150})',
                r'(?:this|we)\s+(?:aims?|intends?)\s+to\s+([^\n]{15,150})',
                r'(?:designed|built)\s+(?:for|to)\s+([^\n]{15,150})'
            ]

            for pattern in goal_patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                analysis['stated_goals'].extend([m.strip() for m in matches[:2]])

            if insight['key_points']:
                analysis['documentation_insights'].append(insight)

        return analysis

    def analyze_patch_content(self, comparison: Dict) -> Dict[str, Any]:
        """
        Analyze actual code patches to detect meaningful changes like new functions,
        enhancements, and environment adjustments vs. simple configuration updates.
        """
        analysis = {
            'new_functions_detected': [],
            'new_classes_detected': [],
            'enhanced_functions': [],
            'environment_adjustments': [],
            'config_only_changes': [],
            'code_additions_count': 0,
            'config_additions_count': 0,
            'has_meaningful_code_changes': False,
            'meaningfulness_signals': []
        }

        if not comparison or 'files' not in comparison:
            return analysis

        files = comparison['files']

        # File extensions that are purely configuration (not code)
        config_extensions = {'.yml', '.yaml', '.json', '.toml', '.ini', '.conf',
                           '.env', '.properties', '.cfg', '.config', '.xml'}

        # File extensions that are code
        code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rb', '.php',
                          '.cpp', '.c', '.h', '.cs', '.swift', '.kt', '.rs',
                          '.jsx', '.tsx', '.vue', '.scala', '.sh', '.bash'}

        for file_data in files:
            filename = file_data.get('filename', '')
            patch = file_data.get('patch', '')
            additions = file_data.get('additions', 0)
            status = file_data.get('status', '')

            if not patch:
                continue

            file_ext = Path(filename).suffix.lower()
            filename_lower = filename.lower()

            # Categorize file type
            is_code_file = file_ext in code_extensions
            is_config_file = file_ext in config_extensions or any(x in filename_lower for x in ['config', '.env', 'settings'])
            is_docker_env = any(x in filename_lower for x in ['docker', 'kubernetes', 'k8s', '.yml', '.yaml'])

            # Track additions by type
            if is_code_file:
                analysis['code_additions_count'] += additions
            elif is_config_file:
                analysis['config_additions_count'] += additions

            # Skip analysis for non-code files unless they're environment-related
            if not is_code_file and not is_docker_env:
                if is_config_file:
                    analysis['config_only_changes'].append(filename)
                continue

            # Analyze patch content for meaningful patterns
            patch_lines = patch.split('\n')
            added_lines = [line[1:].strip() for line in patch_lines if line.startswith('+') and not line.startswith('+++')]

            # Detect new function definitions
            function_patterns = {
                'python': r'^\+\s*def\s+(\w+)\s*\(',
                'javascript': r'^\+\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\()',
                'java': r'^\+\s*(?:public|private|protected)?\s*(?:static\s+)?[\w<>]+\s+(\w+)\s*\(',
                'go': r'^\+\s*func\s+(\w+)\s*\(',
                'typescript': r'^\+\s*(?:function\s+(\w+)|(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\()',
                'c/cpp': r'^\+\s*[\w\*]+\s+(\w+)\s*\([^)]*\)\s*\{',
            }

            class_patterns = {
                'python': r'^\+\s*class\s+(\w+)',
                'javascript': r'^\+\s*class\s+(\w+)',
                'java': r'^\+\s*(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)',
                'typescript': r'^\+\s*(?:export\s+)?class\s+(\w+)',
                'cpp': r'^\+\s*class\s+(\w+)',
            }

            # Check for new functions
            for line in patch_lines:
                for lang, pattern in function_patterns.items():
                    matches = re.findall(pattern, line)
                    if matches:
                        # Flatten matches (some patterns have multiple groups)
                        func_names = [m for m in (matches[0] if isinstance(matches[0], tuple) else [matches[0]]) if m]
                        for func_name in func_names:
                            analysis['new_functions_detected'].append({
                                'file': filename,
                                'function': func_name,
                                'language': lang
                            })
                            analysis['meaningfulness_signals'].append(f"New function: {func_name} in {filename}")

                # Check for new classes
                for lang, pattern in class_patterns.items():
                    matches = re.findall(pattern, line)
                    if matches:
                        for class_name in matches:
                            analysis['new_classes_detected'].append({
                                'file': filename,
                                'class': class_name,
                                'language': lang
                            })
                            analysis['meaningfulness_signals'].append(f"New class: {class_name} in {filename}")

            # Detect environment-specific adjustments (Docker, K8s, cloud configs with substance)
            if is_docker_env and additions > 5:
                # Check if it's not just path changes
                substantial_lines = [l for l in added_lines if len(l) > 20 and not l.startswith('#')]
                if len(substantial_lines) > 3:
                    analysis['environment_adjustments'].append({
                        'file': filename,
                        'type': 'docker/kubernetes' if 'docker' in filename_lower or 'k8s' in filename_lower else 'deployment',
                        'additions': additions
                    })
                    analysis['meaningfulness_signals'].append(f"Environment adjustment in {filename}")

            # Detect enhancements to existing functions (modifications to function bodies)
            # Look for modified functions with substantial additions
            if is_code_file and status == 'modified' and additions > 10:
                # Check if there are function calls, logic, or algorithmic changes
                logic_indicators = ['if ', 'for ', 'while ', 'return ', 'await ', 'async ',
                                  'try:', 'except:', 'catch ', 'throw ', '&&', '||',
                                  'map(', 'filter(', 'reduce(', 'forEach(']

                has_logic = any(indicator in line for line in added_lines for indicator in logic_indicators)
                if has_logic:
                    analysis['enhanced_functions'].append({
                        'file': filename,
                        'additions': additions
                    })
                    analysis['meaningfulness_signals'].append(f"Enhanced logic in {filename}")

        # Determine if changes are meaningful overall
        has_new_functions = len(analysis['new_functions_detected']) > 0
        has_new_classes = len(analysis['new_classes_detected']) > 0
        has_enhancements = len(analysis['enhanced_functions']) > 0
        has_env_adjustments = len(analysis['environment_adjustments']) > 0
        has_substantial_code = analysis['code_additions_count'] > 50

        # Changes are meaningful if they have:
        # - New functions or classes (new capabilities)
        # - Enhancements to existing code
        # - Environment adjustments with substance
        # - Substantial code additions (not just config)
        analysis['has_meaningful_code_changes'] = (
            has_new_functions or
            has_new_classes or
            has_enhancements or
            has_env_adjustments or
            has_substantial_code
        )

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

    def classify_fork_meaningfulness(self, patch_analysis: Dict, file_analysis: Dict) -> Dict[str, Any]:
        """
        Classify whether the fork contains meaningful or not meaningful changes.

        Meaningful: new functions, environment adjustments, enhancements
        Not meaningful: simple config updates, path changes, documentation only
        """
        classification = {
            'is_meaningful': False,
            'classification': 'Not Meaningful',
            'confidence': 'low',
            'reasons': [],
            'summary': ''
        }

        # Evidence for meaningful changes
        new_functions_count = len(patch_analysis.get('new_functions_detected', []))
        new_classes_count = len(patch_analysis.get('new_classes_detected', []))
        enhanced_functions_count = len(patch_analysis.get('enhanced_functions', []))
        env_adjustments_count = len(patch_analysis.get('environment_adjustments', []))
        code_additions = patch_analysis.get('code_additions_count', 0)
        config_additions = patch_analysis.get('config_additions_count', 0)
        meaningfulness_signals = patch_analysis.get('meaningfulness_signals', [])

        # Evidence for not meaningful
        config_only_changes = patch_analysis.get('config_only_changes', [])
        total_files = file_analysis.get('total_files_changed', 0)
        categories = file_analysis.get('change_categories', set())

        # Calculate meaningfulness score
        meaningful_score = 0

        # Strong indicators of meaningful work
        if new_functions_count > 0:
            meaningful_score += new_functions_count * 10
            classification['reasons'].append(f"{new_functions_count} new function(s) added")

        if new_classes_count > 0:
            meaningful_score += new_classes_count * 15
            classification['reasons'].append(f"{new_classes_count} new class(es) added")

        if enhanced_functions_count > 0:
            meaningful_score += enhanced_functions_count * 5
            classification['reasons'].append(f"{enhanced_functions_count} function(s) enhanced with new logic")

        if env_adjustments_count > 0:
            meaningful_score += env_adjustments_count * 8
            classification['reasons'].append(f"{env_adjustments_count} environment adjustment(s) for deployment")

        if code_additions > 100:
            meaningful_score += 20
            classification['reasons'].append(f"{code_additions} lines of code added")
        elif code_additions > 50:
            meaningful_score += 10
            classification['reasons'].append(f"{code_additions} lines of code added")

        # Negative indicators (only config/doc changes)
        if total_files > 0:
            config_ratio = len(config_only_changes) / total_files

            # If more than 80% of changes are config-only, reduce score
            if config_ratio > 0.8:
                meaningful_score -= 15
                if not classification['reasons']:  # Only add if no other reasons
                    classification['reasons'].append(f"{len(config_only_changes)} configuration file(s) changed")

            # Documentation-only changes
            if 'documentation' in categories and len(categories) == 1:
                meaningful_score -= 10
                if not classification['reasons']:
                    classification['reasons'].append("Only documentation changes")

        # Determine classification
        if meaningful_score >= 20:
            classification['is_meaningful'] = True
            classification['classification'] = 'Meaningful'
            classification['confidence'] = 'high'
        elif meaningful_score >= 10:
            classification['is_meaningful'] = True
            classification['classification'] = 'Meaningful'
            classification['confidence'] = 'medium'
        elif meaningful_score >= 5:
            classification['is_meaningful'] = True
            classification['classification'] = 'Likely Meaningful'
            classification['confidence'] = 'low'
        else:
            classification['is_meaningful'] = False
            classification['classification'] = 'Not Meaningful'
            classification['confidence'] = 'medium' if meaningful_score < -5 else 'low'

            if not classification['reasons']:
                classification['reasons'].append("No significant code changes detected")

        # Build summary
        if classification['is_meaningful']:
            if new_functions_count > 0 or new_classes_count > 0:
                classification['summary'] = "Fork adds new functionality to the codebase"
            elif env_adjustments_count > 0:
                classification['summary'] = "Fork adapts the project for different environments"
            elif enhanced_functions_count > 0:
                classification['summary'] = "Fork enhances existing functionality"
            else:
                classification['summary'] = "Fork includes substantial code modifications"
        else:
            if config_ratio > 0.8 if total_files > 0 else False:
                classification['summary'] = "Fork primarily contains configuration updates"
            elif 'documentation' in categories and len(categories) <= 2:
                classification['summary'] = "Fork primarily contains documentation changes"
            else:
                classification['summary'] = "Fork contains minor or non-functional changes"

        return classification

    def generate_executive_summary(self, fork_data: Dict, file_analysis: Dict,
                                   commit_analysis: Dict, readme_changed: bool,
                                   readme_analysis: Dict, doc_analysis: Dict,
                                   meaningfulness: Dict = None) -> str:
        """
        Generate an executive-level summary suitable for senior management.
        Focus on ACTUAL PURPOSE and BUSINESS INTENT from documentation.
        """
        fork_owner = fork_data['fork_owner']
        original_repo = fork_data['original_repo']
        owner_type = fork_data.get('fork_owner_type', 'User')

        summary_parts = []

        # Opening - Who and what
        files_changed = file_analysis.get('total_files_changed', 0)
        if owner_type == 'Organization':
            summary_parts.append(f"Organization '{fork_owner}' has developed a customized version of {original_repo} with {files_changed} files modified.")
        else:
            summary_parts.append(f"Developer '{fork_owner}' has created a fork of {original_repo} with {files_changed} file modifications.")

        # Add meaningfulness classification prominently
        if meaningfulness:
            classification = meaningfulness.get('classification', 'Unknown')
            reasons = meaningfulness.get('reasons', [])
            if meaningfulness.get('is_meaningful'):
                if reasons:
                    reason_text = '; '.join(reasons[:2])
                    summary_parts.append(f"MEANINGFUL CHANGES: {reason_text}.")
            else:
                if reasons:
                    reason_text = reasons[0]
                    summary_parts.append(f"NOT MEANINGFUL: {reason_text}.")

        # PRIORITY 1: Use stated purpose from README if available
        if readme_analysis.get('stated_purpose'):
            purpose = readme_analysis['stated_purpose']
            summary_parts.append(f"The fork explicitly states it is {purpose}.")

        # PRIORITY 2: Use stated goals from documentation
        elif doc_analysis.get('stated_goals'):
            goal = doc_analysis['stated_goals'][0]
            summary_parts.append(f"Documentation indicates the goal is to {goal}.")

        # PRIORITY 3: Use business context from README analysis
        elif readme_analysis.get('business_context'):
            summary_parts.append(readme_analysis['business_context'])

        # PRIORITY 4: Use use cases from README
        elif readme_analysis.get('use_cases'):
            use_case = readme_analysis['use_cases'][0]
            summary_parts.append(f"The fork is {use_case}.")

        # Add industry/domain context if detected
        industry_terms = readme_analysis.get('industry_terms', [])
        if industry_terms:
            industries = ' and '.join(industry_terms[:2])
            if readme_analysis.get('target_audience'):
                audience = readme_analysis['target_audience']
                summary_parts.append(f"This appears to be targeted at {audience} in the {industries} space.")
            else:
                summary_parts.append(f"The fork is focused on {industries} applications.")

        # Add deployment/integration details from docs
        doc_insights = doc_analysis.get('documentation_insights', [])
        if doc_insights:
            deployment_docs = [d for d in doc_insights if d['type'] == 'deployment']
            if deployment_docs and deployment_docs[0]['key_points']:
                points = ', '.join(deployment_docs[0]['key_points'][:3])
                summary_parts.append(f"Deployment documentation covers {points}.")

        # Add integration mentions
        integrations = readme_analysis.get('integrations_mentioned', [])
        if integrations:
            int_list = ', '.join(integrations[:3])
            summary_parts.append(f"Integrations mentioned include {int_list}.")

        # Add problems being solved
        problems = readme_analysis.get('problems_solved', [])
        if problems and not readme_analysis.get('stated_purpose'):  # Don't duplicate if we already have purpose
            problem = problems[0]
            summary_parts.append(f"The changes address {problem}.")

        # Fallback to technical details if no documentation insights
        if len(summary_parts) == 1:  # Only have the opening
            specific_details = self._extract_specific_changes(file_analysis, commit_analysis)
            if specific_details:
                summary_parts.append(specific_details)

            business_context = self._infer_business_context(fork_data, file_analysis, commit_analysis)
            if business_context:
                summary_parts.append(business_context)

        # Combine into executive summary (aim for 4-5 sentences with actual business meaning)
        summary = ' '.join(summary_parts[:5])
        return summary if len(summary) > 50 else "Fork analysis incomplete - insufficient documentation to determine business purpose."

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

        # Get detailed owner information
        print("  Getting owner profile information...")
        owner_details = self.get_owner_details(fork_owner)

        insights = {
            'fork_owner': fork_owner,
            'fork_name': fork_name,
            'fork_url': fork_data.get('fork_url', ''),
            'fork_owner_url': fork_data.get('fork_owner_url', ''),
            'original_repo': original_repo,
            'original_url': fork_data.get('original_url', ''),
            'commits_ahead': fork_data.get('commits_ahead', 0),
            'comparison_url': '',  # Will be filled in after we get branch info
            'owner_details': owner_details
        }

        # Get detailed comparison between repos
        print("  Fetching code changes...")
        comparison = self.get_comparison(original_owner, original_name, fork_owner, fork_name)

        if not comparison:
            print(f"  ERROR: Could not fetch comparison data")
            insights['summary'] = f"Unable to analyze fork by {fork_owner}. The repository may be private or inaccessible."
            insights['error'] = 'comparison_failed'
            return insights

        # Build comparison URL for easy access to GitHub's diff view
        # Get branch information from the repos
        base_data = self._make_request(f"{self.base_url}/repos/{original_owner}/{original_name}")
        head_data = self._make_request(f"{self.base_url}/repos/{fork_owner}/{fork_name}")

        if base_data and head_data:
            base_branch = base_data.get('default_branch', 'main')
            head_branch = head_data.get('default_branch', 'main')
            insights['comparison_url'] = f"https://github.com/{original_owner}/{original_name}/compare/{base_branch}...{fork_owner}:{head_branch}"
            print(f"  Comparison URL: {insights['comparison_url']}")

        # Debug: Show what we got
        files_count = len(comparison.get('files', []))
        commits_count = len(comparison.get('commits', []))
        print(f"  Found {commits_count} commits and {files_count} files changed")

        # Analyze actual file changes
        print("  Analyzing file modifications...")
        file_analysis = self.analyze_file_changes(comparison)
        insights['file_analysis'] = file_analysis

        # Analyze patch content for meaningful changes
        print("  Analyzing code patches for meaningful changes...")
        patch_analysis = self.analyze_patch_content(comparison)
        insights['patch_analysis'] = patch_analysis

        # Classify meaningfulness of changes
        print("  Classifying fork meaningfulness...")
        meaningfulness = self.classify_fork_meaningfulness(patch_analysis, file_analysis)
        insights['meaningfulness'] = meaningfulness
        print(f"  Classification: {meaningfulness['classification']} (confidence: {meaningfulness['confidence']})")

        # Analyze commit content for business intent
        print("  Understanding development intent...")
        commit_analysis = self.analyze_commit_content(comparison)
        insights['commit_analysis'] = commit_analysis

        # Deep analysis of README changes
        print("  Analyzing README for business purpose...")
        original_readme = self.get_readme(original_owner, original_name)
        fork_readme = self.get_readme(fork_owner, fork_name)
        readme_analysis = self.analyze_readme_deeply(original_readme, fork_readme)
        insights['readme_analysis'] = readme_analysis

        # Analyze new documentation files
        print("  Reading new documentation files...")
        new_doc_files = file_analysis.get('new_files_added', [])
        doc_analysis = self.analyze_documentation_files(fork_owner, fork_name, new_doc_files)
        insights['documentation_analysis'] = doc_analysis

        # Check if README changed
        readme_changed = fork_data.get('readme_changed', '').lower() == 'true'

        # Generate executive summary with all insights
        print("  Generating executive summary...")
        summary = self.generate_executive_summary(fork_data, file_analysis,
                                                  commit_analysis, readme_changed,
                                                  readme_analysis, doc_analysis,
                                                  meaningfulness)
        insights['summary'] = summary

        print(f"\n  Executive Summary:\n  {summary}\n")

        return insights

    def process_csv(self, input_file: str) -> List[Dict[str, Any]]:
        """Process the CSV file and analyze forks."""
        all_insights = []

        print(f"Reading active forks from: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            forks = list(reader)

        if len(forks) == 0:
            print("No forks found in CSV file")
            return []

        # Process forks (all or limited)
        if self.max_forks is not None:
            forks_to_process = forks[:self.max_forks]
            print(f"Processing first {self.max_forks} of {len(forks)} forks...\n")
        else:
            forks_to_process = forks
            print(f"Processing all {len(forks)} forks...\n")

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
                f.write(f"   Based on: {insight['original_repo']}\n")

                # Add comparison URL prominently for easy review
                if insight.get('comparison_url'):
                    f.write(f"\n   >>> VIEW CHANGES: {insight['comparison_url']} <<<\n")

                f.write("\n")

                # Add meaningfulness classification prominently
                if 'meaningfulness' in insight:
                    meaningfulness = insight['meaningfulness']
                    classification = meaningfulness.get('classification', 'Unknown')
                    confidence = meaningfulness.get('confidence', 'unknown')
                    is_meaningful = meaningfulness.get('is_meaningful', False)

                    # Use distinctive markers for meaningful vs not meaningful
                    marker = "✓" if is_meaningful else "✗"
                    f.write(f"   CHANGE CLASSIFICATION: [{marker}] {classification.upper()} (confidence: {confidence})\n")

                    # Add reasons
                    reasons = meaningfulness.get('reasons', [])
                    if reasons:
                        f.write(f"   Reasons: {'; '.join(reasons)}\n")

                    # Add summary
                    summary = meaningfulness.get('summary', '')
                    if summary:
                        f.write(f"   {summary}\n")

                    f.write("\n")

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

                # Add detailed meaningfulness signals if available
                if 'patch_analysis' in insight:
                    patch_analysis = insight['patch_analysis']

                    # Show specific functions and classes detected
                    new_functions = patch_analysis.get('new_functions_detected', [])
                    new_classes = patch_analysis.get('new_classes_detected', [])
                    enhanced_functions = patch_analysis.get('enhanced_functions', [])
                    env_adjustments = patch_analysis.get('environment_adjustments', [])

                    if new_functions or new_classes or enhanced_functions or env_adjustments:
                        f.write(f"\n   Detailed Analysis:\n")

                        if new_functions:
                            f.write(f"   New Functions Added ({len(new_functions)}):\n")
                            for func in new_functions[:5]:  # Show first 5
                                f.write(f"      - {func['function']}() in {func['file']}\n")
                            if len(new_functions) > 5:
                                f.write(f"      ... and {len(new_functions) - 5} more\n")

                        if new_classes:
                            f.write(f"   New Classes Added ({len(new_classes)}):\n")
                            for cls in new_classes[:5]:
                                f.write(f"      - {cls['class']} in {cls['file']}\n")
                            if len(new_classes) > 5:
                                f.write(f"      ... and {len(new_classes) - 5} more\n")

                        if enhanced_functions:
                            f.write(f"   Enhanced Functions ({len(enhanced_functions)}):\n")
                            for enh in enhanced_functions[:5]:
                                f.write(f"      - {enh['file']} (+{enh['additions']} lines)\n")
                            if len(enhanced_functions) > 5:
                                f.write(f"      ... and {len(enhanced_functions) - 5} more\n")

                        if env_adjustments:
                            f.write(f"   Environment Adjustments ({len(env_adjustments)}):\n")
                            for env in env_adjustments[:3]:
                                f.write(f"      - {env['file']} ({env['type']})\n")

                    # Show code vs config stats
                    code_additions = patch_analysis.get('code_additions_count', 0)
                    config_additions = patch_analysis.get('config_additions_count', 0)
                    if code_additions > 0 or config_additions > 0:
                        f.write(f"\n   Code Statistics:\n")
                        f.write(f"      Code additions: {code_additions} lines\n")
                        f.write(f"      Config additions: {config_additions} lines\n")

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

    # Initialize analyzer (process all forks)
    analyzer = ForkInsightsAnalyzer(token)

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
