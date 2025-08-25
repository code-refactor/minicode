"""
HTML exporter for the File System Analyzer unified library.
"""

import json
from datetime import datetime
from typing import Any, List, Dict, Optional
from pathlib import Path

from ..core.types import FilePath
from .base import BaseExporter


class HtmlExporter(BaseExporter):
    """HTML report exporter."""
    
    def export(
        self, 
        data: Any, 
        output_path: FilePath, 
        title: str = "Analysis Report",
        template_path: Optional[FilePath] = None,
        **kwargs
    ) -> bool:
        """Export data as HTML report."""
        try:
            serializable_data = self._ensure_serializable(data)
            
            # Use custom template or default
            if template_path and Path(template_path).exists():
                template = Path(template_path).read_text()
            else:
                template = self._get_default_template()
                
            # Generate report content
            content = self._generate_report_content(serializable_data)
            summary = self._generate_summary(serializable_data)
            recommendations = self._generate_recommendations(serializable_data)
            
            # Format the HTML
            html_content = template.format(
                title=title,
                timestamp=datetime.now().isoformat(),
                summary=summary,
                content=content,
                recommendations=recommendations,
                raw_data=json.dumps(serializable_data, indent=2)
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting HTML to {output_path}: {e}")
            return False
            
    def _get_default_template(self) -> str:
        """Get default HTML template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .summary {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .recommendations {{ background: #f0f8f0; padding: 15px; border-radius: 5px; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .high {{ color: #f57c00; font-weight: bold; }}
        .medium {{ color: #fbc02d; }}
        .low {{ color: #388e3c; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        .collapsible {{ cursor: pointer; background: #777; color: white; padding: 10px; border: none; width: 100%; text-align: left; }}
        .content {{ display: none; padding: 0 18px; background-color: #f1f1f1; }}
        .active {{ background-color: #555; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on: {timestamp}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="summary">{summary}</div>
    </div>
    
    <div class="section">
        <h2>Analysis Results</h2>
        {content}
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <div class="recommendations">{recommendations}</div>
    </div>
    
    <div class="section">
        <button type="button" class="collapsible">Raw Data (JSON)</button>
        <div class="content">
            <pre>{raw_data}</pre>
        </div>
    </div>
    
    <script>
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {{
            coll[i].addEventListener("click", function() {{
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                content.style.display = content.style.display === "block" ? "none" : "block";
            }});
        }}
    </script>
</body>
</html>'''
        
    def _generate_summary(self, data: Dict[str, Any]) -> str:
        """Generate summary section."""
        summary_parts = []
        
        if 'total_files_processed' in data:
            summary_parts.append(f"Files Processed: {data['total_files_processed']}")
        if 'files_with_findings' in data:
            summary_parts.append(f"Files with Findings: {data['files_with_findings']}")
        if 'total_findings' in data:
            summary_parts.append(f"Total Findings: {data['total_findings']}")
            
        return '<br>'.join(summary_parts) if summary_parts else 'No summary available'
        
    def _generate_report_content(self, data: Dict[str, Any]) -> str:
        """Generate main content section."""
        content_parts = []
        
        if 'scan_results' in data:
            content_parts.append(self._format_scan_results(data['scan_results']))
        if 'matches' in data:
            content_parts.append(self._format_matches(data['matches']))
            
        return '<br>'.join(content_parts) if content_parts else 'No content available'
        
    def _generate_recommendations(self, data: Dict[str, Any]) -> str:
        """Generate recommendations section."""
        recommendations = data.get('recommendations', [])
        if not recommendations:
            return 'No recommendations available'
            
        html_parts = []
        for rec in recommendations:
            priority = rec.get('priority', 'medium')
            html_parts.append(
                f'<div class="{priority}"><strong>{rec.get("title", "Recommendation")}</strong><br>'
                f'{rec.get("description", "No description")}</div>'
            )
            
        return '<br>'.join(html_parts)
        
    def _format_scan_results(self, scan_results: List[Any]) -> str:
        """Format scan results for HTML display."""
        if not scan_results:
            return 'No scan results available'
        
        html_parts = []
        for result in scan_results:
            if hasattr(result, '__dict__'):
                result_dict = result.__dict__
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {'result': str(result)}
                
            html_parts.append(f'<div><strong>Result:</strong> {result_dict}</div>')
        
        return '<br>'.join(html_parts)
        
    def _format_matches(self, matches: List[Any]) -> str:
        """Format matches for HTML display."""
        if not matches:
            return 'No matches found'
            
        html_parts = []
        for match in matches:
            if hasattr(match, '__dict__'):
                match_dict = match.__dict__
            elif isinstance(match, dict):
                match_dict = match
            else:
                match_dict = {'match': str(match)}
                
            priority = match_dict.get('priority', 'medium')
            html_parts.append(
                f'<div class="{priority}"><strong>Match:</strong> {match_dict}</div>'
            )
        
        return '<br>'.join(html_parts)
        
    def get_supported_formats(self) -> List[str]:
        """Get supported formats."""
        return ['html']
        
    def validate_configuration(self) -> bool:
        """
        Validate the HtmlExporter configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        # Validate base configuration (output directory)
        return super().validate()