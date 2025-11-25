#!/usr/bin/env python3
"""
GitHub Fork Analysis - HTML Presentation Generator

Generates a self-contained HTML dashboard from fork analysis JSON data.
Perfect for sharing with senior management via Slack or email.

Usage:
    python generate_presentation.py <input_json_file>

Example:
    python generate_presentation.py ../03_github_org_active_forks_insights/fork_insights_executive_20251121_193948.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Embedded Chart.js library for offline use
CHARTJS_CODE = None  # Will be loaded on first use


class PresentationGenerator:
    """Generates an interactive HTML dashboard from fork analysis data."""

    def __init__(self, data: List[Dict[str, Any]]):
        """Initialize with parsed JSON data."""
        self.data = data
        self.stats = self._calculate_statistics()

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate summary statistics from the data."""
        total = len(self.data)
        meaningful = sum(1 for item in self.data
                        if item.get('meaningfulness', {}).get('is_meaningful', False))
        not_meaningful = total - meaningful

        # Count by confidence level
        high_confidence = sum(1 for item in self.data
                             if item.get('meaningfulness', {}).get('confidence') == 'high')
        medium_confidence = sum(1 for item in self.data
                               if item.get('meaningfulness', {}).get('confidence') == 'medium')
        low_confidence = sum(1 for item in self.data
                            if item.get('meaningfulness', {}).get('confidence') == 'low')

        # Total changes (handle string/int conversions)
        total_files = sum(int(item.get('file_analysis', {}).get('total_files_changed', 0) or 0)
                         for item in self.data)
        total_commits = sum(int(item.get('commits_ahead', 0) or 0) for item in self.data)

        # Code vs config
        total_code = sum(int(item.get('patch_analysis', {}).get('code_additions_count', 0) or 0)
                        for item in self.data)
        total_config = sum(int(item.get('patch_analysis', {}).get('config_additions_count', 0) or 0)
                          for item in self.data)

        # New functions/classes
        total_functions = sum(len(item.get('patch_analysis', {}).get('new_functions_detected', []))
                             for item in self.data)
        total_classes = sum(len(item.get('patch_analysis', {}).get('new_classes_detected', []))
                           for item in self.data)

        return {
            'total': total,
            'meaningful': meaningful,
            'not_meaningful': not_meaningful,
            'meaningful_percent': round(meaningful / total * 100, 1) if total > 0 else 0,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'total_files': total_files,
            'total_commits': total_commits,
            'total_code': total_code,
            'total_config': total_config,
            'total_functions': total_functions,
            'total_classes': total_classes
        }

    def generate_html(self) -> str:
        """Generate the complete HTML dashboard."""
        # Load Chart.js library
        chartjs_code = self._get_chartjs_library()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Fork Analysis - Executive Dashboard</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header()}
        {self._generate_summary_stats()}
        {self._generate_charts()}
        {self._generate_filters()}
        {self._generate_fork_list()}
    </div>
    <script>
        {chartjs_code}
    </script>
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""
        return html

    def _get_chartjs_library(self) -> str:
        """Get Chart.js library code (embedded for offline use)."""
        global CHARTJS_CODE

        if CHARTJS_CODE is None:
            # Try to load from the downloaded file
            chartjs_path = Path(__file__).parent / 'chart.min.js'

            # If not found locally, try to download it
            if not chartjs_path.exists():
                print("  Downloading Chart.js library for embedding...")
                import urllib.request
                try:
                    url = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
                    with urllib.request.urlopen(url) as response:
                        CHARTJS_CODE = response.read().decode('utf-8')
                    # Save for future use
                    with open(chartjs_path, 'w', encoding='utf-8') as f:
                        f.write(CHARTJS_CODE)
                    print("  Chart.js library downloaded and cached")
                except Exception as e:
                    print(f"  Warning: Could not download Chart.js: {e}")
                    print("  Falling back to CDN (requires internet)")
                    return '// Chart.js will be loaded from CDN if this fails'
            else:
                with open(chartjs_path, 'r', encoding='utf-8') as f:
                    CHARTJS_CODE = f.read()

        return CHARTJS_CODE

    def _get_css(self) -> str:
        """Return embedded CSS styles."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        @media print {
            body {
                background: white;
                padding: 0;
            }
            .container {
                max-width: 100%;
                box-shadow: none;
                border-radius: 0;
            }
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px 20px;
            text-align: center;
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 8px;
            font-weight: 700;
        }

        .header p {
            font-size: 0.95em;
            opacity: 0.95;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            padding: 20px;
            background: #f8f9fa;
        }

        @media print {
            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
                padding: 15px;
            }
        }

        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 3px;
        }

        .stat-label {
            font-size: 0.75em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .charts-section {
            padding: 20px;
            background: white;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            margin-top: 15px;
            max-width: 500px;
            margin-left: auto;
            margin-right: auto;
        }

        @media print {
            .charts-grid {
                grid-template-columns: repeat(2, 1fr);
                max-width: 100%;
                gap: 10px;
            }
        }

        .chart-container {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .chart-container h3 {
            margin-bottom: 12px;
            color: #333;
            font-size: 1.1em;
        }

        .filters {
            padding: 15px 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            border-bottom: 1px solid #e0e0e0;
        }

        .filter-group {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }

        .filter-group label {
            font-weight: 600;
            color: #555;
        }

        .filter-group input,
        .filter-group select {
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.2s;
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .filter-group input[type="search"] {
            flex: 1;
            min-width: 300px;
        }

        .fork-list {
            padding: 20px;
        }

        .fork-item {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: all 0.3s;
        }

        @media print {
            .fork-list {
                padding: 10px;
            }
            .fork-item {
                padding: 12px;
                margin-bottom: 20px;
            }
        }

        .fork-item:hover {
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }

        .fork-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
            cursor: pointer;
        }

        .fork-title {
            flex: 1;
        }

        .fork-title h3 {
            font-size: 1.3em;
            color: #333;
            margin-bottom: 4px;
        }

        .fork-title a {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }

        .fork-title a:hover {
            text-decoration: underline;
        }

        .badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            color-adjust: exact;
        }

        .badge.meaningful {
            background: #10b981 !important;
            color: white !important;
            border: 2px solid #059669;
        }

        .badge.not-meaningful {
            background: #ef4444 !important;
            color: white !important;
            border: 2px solid #dc2626;
        }

        .badge.likely-meaningful {
            background: #f59e0b !important;
            color: white !important;
            border: 2px solid #d97706;
        }

        .confidence {
            font-size: 0.85em;
            color: #666;
            margin-left: 10px;
        }

        .fork-summary {
            color: #555;
            line-height: 1.8;
            margin: 15px 0;
        }

        .fork-details {
            display: none;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
        }

        .fork-details.expanded {
            display: block;
        }

        .detail-section {
            margin-bottom: 20px;
        }

        .detail-section h4 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }

        .detail-section ul {
            list-style: none;
            padding-left: 0;
        }

        .detail-section li {
            padding: 5px 0;
            color: #555;
        }

        .detail-section li:before {
            content: "→ ";
            color: #667eea;
            font-weight: bold;
            margin-right: 5px;
        }

        .view-changes-btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 15px;
            transition: background 0.2s;
        }

        .view-changes-btn:hover {
            background: #5568d3;
        }

        .toggle-details {
            background: none;
            border: none;
            color: #667eea;
            font-size: 0.9em;
            cursor: pointer;
            padding: 5px 10px;
            font-weight: 600;
        }

        .toggle-details:hover {
            text-decoration: underline;
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 12px;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }

        @media print {
            .stats-row {
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
                padding: 8px;
            }
        }

        .stat-item {
            text-align: center;
        }

        .stat-item .value {
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }

        .stat-item .label {
            font-size: 0.75em;
            color: #666;
        }

        .no-results {
            text-align: center;
            padding: 60px;
            color: #999;
            font-size: 1.2em;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }

            .charts-grid {
                grid-template-columns: 1fr;
            }

            .filter-group {
                flex-direction: column;
                align-items: stretch;
            }

            .filter-group input[type="search"] {
                min-width: 100%;
            }
        }

        /* Additional print styles for PDF export */
        @media print {
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }

            .header {
                background: #667eea !important;
                background-color: #667eea !important;
                page-break-after: avoid;
            }

            .fork-item {
                page-break-inside: avoid;
                margin-bottom: 30px;
            }

            .filters {
                display: none;
            }

            .toggle-details {
                display: none;
            }

            .fork-details {
                display: block !important;
            }

            .badge.meaningful {
                background: #10b981 !important;
                background-color: #10b981 !important;
                color: white !important;
            }

            .badge.not-meaningful {
                background: #ef4444 !important;
                background-color: #ef4444 !important;
                color: white !important;
            }

            .badge.likely-meaningful {
                background: #f59e0b !important;
                background-color: #f59e0b !important;
                color: white !important;
            }

            .stat-value {
                color: #667eea !important;
            }

            a {
                color: #667eea;
                text-decoration: none;
            }

            a[href]:after {
                content: " (" attr(href) ")";
                font-size: 0.8em;
                color: #666;
            }
        }
        """

    def _generate_header(self) -> str:
        """Generate the header section."""
        return f"""
        <div class="header">
            <h1>GitHub Fork Analysis</h1>
            <p>Executive Dashboard - Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        """

    def _generate_summary_stats(self) -> str:
        """Generate the summary statistics cards."""
        stats = self.stats
        return f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total']}</div>
                <div class="stat-label">Total Forks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #10b981;">{stats['meaningful']}</div>
                <div class="stat-label">Meaningful</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #ef4444;">{stats['not_meaningful']}</div>
                <div class="stat-label">Not Meaningful</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['meaningful_percent']}%</div>
                <div class="stat-label">Meaningful Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_functions']}</div>
                <div class="stat-label">New Functions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_classes']}</div>
                <div class="stat-label">New Classes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_files']}</div>
                <div class="stat-label">Files Changed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_code']:,}</div>
                <div class="stat-label">Lines of Code</div>
            </div>
        </div>
        """

    def _generate_charts(self) -> str:
        """Generate the charts section."""
        return f"""
        <div class="charts-section">
            <h2 style="margin-bottom: 10px;">Analysis Overview</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>Meaningfulness Distribution</h3>
                    <canvas id="meaningfulnessChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Code vs Configuration</h3>
                    <canvas id="codeConfigChart"></canvas>
                </div>
            </div>
        </div>
        """

    def _generate_filters(self) -> str:
        """Generate the filter controls."""
        return """
        <div class="filters">
            <div class="filter-group">
                <label for="search">Search:</label>
                <input type="search" id="search" placeholder="Search by fork name or owner..." />

                <label for="meaningfulFilter">Filter:</label>
                <select id="meaningfulFilter">
                    <option value="all">All Forks</option>
                    <option value="meaningful">Meaningful Only</option>
                    <option value="not-meaningful">Not Meaningful Only</option>
                </select>

                <label for="sortBy">Sort:</label>
                <select id="sortBy">
                    <option value="default">Default Order</option>
                    <option value="name">Fork Name</option>
                    <option value="files">Files Changed</option>
                    <option value="code">Code Lines</option>
                </select>
            </div>
        </div>
        """

    def _generate_fork_list(self) -> str:
        """Generate the list of forks."""
        forks_html = []

        for i, fork in enumerate(self.data):
            fork_html = self._generate_fork_item(fork, i)
            forks_html.append(fork_html)

        return f"""
        <div class="fork-list" id="forkList">
            {''.join(forks_html)}
            <div id="noResults" class="no-results" style="display: none;">
                No forks match your search criteria.
            </div>
        </div>
        """

    def _generate_fork_item(self, fork: Dict[str, Any], index: int) -> str:
        """Generate HTML for a single fork item."""
        fork_owner = fork.get('fork_owner', 'Unknown')
        fork_name = fork.get('fork_name', 'Unknown')
        fork_url = fork.get('fork_url', '#')
        comparison_url = fork.get('comparison_url', '#')

        # Get owner details
        owner_details = fork.get('owner_details', {})
        real_name = owner_details.get('real_name')
        organization = owner_details.get('organization')
        organization_verified = owner_details.get('organization_verified', False)
        organization_homepage = owner_details.get('organization_homepage')
        organization_url = owner_details.get('organization_url')
        owner_type = owner_details.get('owner_type', 'User')
        bio = owner_details.get('bio')
        location = owner_details.get('location')

        # Build display name
        display_name = real_name if real_name else fork_owner

        # Build organization display with verification badge and link
        org_display = ''
        if organization:
            verified_badge = ' ✓' if organization_verified else ''
            if organization_homepage:
                org_display = f'<a href="{organization_homepage}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: 600;">{organization}{verified_badge}</a>'
            elif organization_url:
                org_display = f'<a href="{organization_url}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: 600;">{organization}{verified_badge}</a>'
            else:
                org_display = f'{organization}{verified_badge}'

        # Build subtitle with additional context
        subtitle_parts = []
        if owner_type == 'Organization':
            subtitle_parts.append('Organization')
        else:
            subtitle_parts.append('Individual Developer')
        if location:
            subtitle_parts.append(location)
        subtitle = ' • '.join(subtitle_parts) if subtitle_parts else ''

        meaningfulness = fork.get('meaningfulness', {})
        is_meaningful = meaningfulness.get('is_meaningful', False)
        classification = meaningfulness.get('classification', 'Unknown')
        confidence = meaningfulness.get('confidence', 'unknown')
        reasons = meaningfulness.get('reasons', [])

        summary = fork.get('summary', 'No summary available.')

        # Badge class
        badge_class = 'meaningful' if is_meaningful else 'not-meaningful'
        if classification == 'Likely Meaningful':
            badge_class = 'likely-meaningful'

        # Get statistics (handle string/int conversions)
        file_analysis = fork.get('file_analysis', {})
        patch_analysis = fork.get('patch_analysis', {})

        files_changed = int(file_analysis.get('total_files_changed', 0) or 0)
        code_lines = int(patch_analysis.get('code_additions_count', 0) or 0)
        config_lines = int(patch_analysis.get('config_additions_count', 0) or 0)

        new_functions = patch_analysis.get('new_functions_detected', [])
        new_classes = patch_analysis.get('new_classes_detected', [])
        enhanced_functions = patch_analysis.get('enhanced_functions', [])

        # Build detailed sections
        details_html = self._generate_fork_details(fork, new_functions, new_classes, enhanced_functions)

        # Data attributes for filtering/sorting
        data_attrs = f'data-meaningful="{str(is_meaningful).lower()}" data-owner="{fork_owner}" data-name="{fork_name}" data-files="{files_changed}" data-code="{code_lines}"'

        reasons_html = ''
        if reasons:
            reasons_html = f'<div style="color: #666; font-size: 0.9em; margin-top: 10px;">Reasons: {"; ".join(reasons)}</div>'

        # Add bio if available
        bio_html = ''
        if bio and len(bio) > 0:
            bio_html = f'<div style="color: #888; font-size: 0.9em; font-style: italic; margin-top: 8px;">"{bio}"</div>'

        # Build organization line
        org_line = ''
        if org_display:
            org_line = f'<div style="font-size: 1.05em; margin-bottom: 6px; color: #333;">Organization: {org_display}</div>'

        return f"""
        <div class="fork-item" {data_attrs}>
            <div class="fork-header" onclick="toggleDetails({index})">
                <div class="fork-title">
                    <h3 style="font-size: 1.4em; color: #667eea; margin-bottom: 5px;">{display_name}</h3>
                    {org_line}
                    <div style="font-size: 0.95em; color: #555; margin-bottom: 4px;">{fork_owner}/{fork_name}</div>
                    {f'<div style="font-size: 0.8em; color: #888; margin-bottom: 5px;">{subtitle}</div>' if subtitle else ''}
                    {bio_html}
                    <a href="{fork_url}" target="_blank" style="font-size: 0.85em;">View Repository →</a>
                </div>
                <div>
                    <span class="badge {badge_class}">{classification}</span>
                    <span class="confidence">{confidence} confidence</span>
                </div>
            </div>

            <div class="fork-summary" style="font-size: 0.95em;">{summary}</div>

            {reasons_html}

            <div class="stats-row">
                <div class="stat-item">
                    <div class="value">{files_changed}</div>
                    <div class="label">Files</div>
                </div>
                <div class="stat-item">
                    <div class="value">{code_lines:,}</div>
                    <div class="label">Code Lines</div>
                </div>
                <div class="stat-item">
                    <div class="value">{len(new_functions)}</div>
                    <div class="label">New Functions</div>
                </div>
                <div class="stat-item">
                    <div class="value">{len(new_classes)}</div>
                    <div class="label">New Classes</div>
                </div>
            </div>

            <a href="{comparison_url}" target="_blank" class="view-changes-btn">View Changes on GitHub →</a>
            <button class="toggle-details" onclick="toggleDetails({index})">Show Details ▼</button>

            <div id="details{index}" class="fork-details">
                {details_html}
            </div>
        </div>
        """

    def _generate_fork_details(self, fork: Dict[str, Any], new_functions: List,
                               new_classes: List, enhanced_functions: List) -> str:
        """Generate detailed analysis section for a fork."""
        sections = []

        # New Functions
        if new_functions:
            funcs_html = '<ul>' + ''.join([
                f'<li>{func.get("function")}() in {func.get("file")}</li>'
                for func in new_functions[:10]
            ]) + '</ul>'
            if len(new_functions) > 10:
                funcs_html += f'<p style="color: #999;">... and {len(new_functions) - 10} more</p>'
            sections.append(f'<div class="detail-section"><h4>New Functions ({len(new_functions)})</h4>{funcs_html}</div>')

        # New Classes
        if new_classes:
            classes_html = '<ul>' + ''.join([
                f'<li>{cls.get("class")} in {cls.get("file")}</li>'
                for cls in new_classes[:10]
            ]) + '</ul>'
            if len(new_classes) > 10:
                classes_html += f'<p style="color: #999;">... and {len(new_classes) - 10} more</p>'
            sections.append(f'<div class="detail-section"><h4>New Classes ({len(new_classes)})</h4>{classes_html}</div>')

        # Enhanced Functions
        if enhanced_functions:
            enh_html = '<ul>' + ''.join([
                f'<li>{enh.get("file")} (+{enh.get("additions")} lines)</li>'
                for enh in enhanced_functions[:10]
            ]) + '</ul>'
            if len(enhanced_functions) > 10:
                enh_html += f'<p style="color: #999;">... and {len(enhanced_functions) - 10} more</p>'
            sections.append(f'<div class="detail-section"><h4>Enhanced Functions ({len(enhanced_functions)})</h4>{enh_html}</div>')

        # Technical Areas
        file_analysis = fork.get('file_analysis', {})
        categories = file_analysis.get('change_categories', [])
        if categories:
            if isinstance(categories, set):
                categories = sorted(list(categories))
            cat_html = ', '.join(categories)
            sections.append(f'<div class="detail-section"><h4>Technical Areas</h4><p>{cat_html}</p></div>')

        return ''.join(sections) if sections else '<p style="color: #999;">No detailed analysis available.</p>'

    def _get_javascript(self) -> str:
        """Return embedded JavaScript for interactivity."""
        return f"""
        // Data for charts
        const stats = {json.dumps(self.stats)};
        const forksData = {json.dumps(self.data)};

        // Initialize charts
        document.addEventListener('DOMContentLoaded', function() {{
            initCharts();
            initFilters();
        }});

        function initCharts() {{
            // Meaningfulness pie chart
            const ctx1 = document.getElementById('meaningfulnessChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'doughnut',
                data: {{
                    labels: ['Meaningful', 'Not Meaningful'],
                    datasets: [{{
                        data: [stats.meaningful, stats.not_meaningful],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                font: {{
                                    size: 14
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Code vs Config bar chart
            const ctx2 = document.getElementById('codeConfigChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: ['Code', 'Configuration'],
                    datasets: [{{
                        label: 'Lines Added',
                        data: [stats.total_code, stats.total_config],
                        backgroundColor: ['#667eea', '#f59e0b'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                font: {{
                                    size: 12
                                }}
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{
                                    size: 12
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function initFilters() {{
            const searchInput = document.getElementById('search');
            const meaningfulFilter = document.getElementById('meaningfulFilter');
            const sortBy = document.getElementById('sortBy');

            searchInput.addEventListener('input', applyFilters);
            meaningfulFilter.addEventListener('change', applyFilters);
            sortBy.addEventListener('change', applyFilters);
        }}

        function applyFilters() {{
            const searchTerm = document.getElementById('search').value.toLowerCase();
            const meaningfulFilter = document.getElementById('meaningfulFilter').value;
            const sortBy = document.getElementById('sortBy').value;

            const forkItems = Array.from(document.querySelectorAll('.fork-item'));
            let visibleCount = 0;

            // Filter
            forkItems.forEach(item => {{
                const owner = item.dataset.owner.toLowerCase();
                const name = item.dataset.name.toLowerCase();
                const isMeaningful = item.dataset.meaningful === 'true';

                let matchesSearch = owner.includes(searchTerm) || name.includes(searchTerm);
                let matchesFilter = meaningfulFilter === 'all' ||
                                   (meaningfulFilter === 'meaningful' && isMeaningful) ||
                                   (meaningfulFilter === 'not-meaningful' && !isMeaningful);

                if (matchesSearch && matchesFilter) {{
                    item.style.display = 'block';
                    visibleCount++;
                }} else {{
                    item.style.display = 'none';
                }}
            }});

            // Show/hide no results message
            document.getElementById('noResults').style.display = visibleCount === 0 ? 'block' : 'none';

            // Sort
            const visibleItems = forkItems.filter(item => item.style.display !== 'none');
            if (sortBy !== 'default') {{
                visibleItems.sort((a, b) => {{
                    if (sortBy === 'name') {{
                        return a.dataset.name.localeCompare(b.dataset.name);
                    }} else if (sortBy === 'files') {{
                        return parseInt(b.dataset.files) - parseInt(a.dataset.files);
                    }} else if (sortBy === 'code') {{
                        return parseInt(b.dataset.code) - parseInt(a.dataset.code);
                    }}
                    return 0;
                }});

                const container = document.getElementById('forkList');
                const noResults = document.getElementById('noResults');
                visibleItems.forEach(item => container.insertBefore(item, noResults));
            }}
        }}

        function toggleDetails(index) {{
            const details = document.getElementById('details' + index);
            details.classList.toggle('expanded');

            const button = details.previousElementSibling;
            if (details.classList.contains('expanded')) {{
                button.textContent = 'Hide Details ▲';
            }} else {{
                button.textContent = 'Show Details ▼';
            }}
        }}
        """


def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python generate_presentation.py <input_json_file>")
        print("\nExample:")
        print("  python generate_presentation.py ../03_github_org_active_forks_insights/fork_insights_executive_20251121_193948.json")
        sys.exit(1)

    input_file = sys.argv[1]

    # Check if input file exists
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    print(f"Reading data from: {input_file}")

    # Load JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} fork records")

    # Generate presentation
    print("Generating HTML presentation...")
    generator = PresentationGenerator(data)
    html_content = generator.generate_html()

    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent
    output_file = output_dir / f"fork_analysis_dashboard_{timestamp}.html"

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"\n{'='*80}")
    print(f"Dashboard generated successfully!")
    print(f"Output file: {output_file}")
    print(f"File size: {file_size_mb:.2f} MB")
    print(f"{'='*80}\n")
    print("The file is 100% SELF-CONTAINED - works completely offline!")
    print("\nYou can now:")
    print("1. Email it as an attachment to your boss")
    print("2. Share it via Slack")
    print("3. Double-click to open in any browser")
    print("4. Works on any device, no internet required!")
    print("\nAll CSS, JavaScript, and Chart.js library are embedded.")


if __name__ == "__main__":
    main()
