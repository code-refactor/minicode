"""Report generator for security findings and vulnerabilities."""

import os
import time
import json
import uuid
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Set, Tuple

import jinja2

from securetask.reporting.redaction import RedactionEngine, RedactionLevel
from securetask.findings.models import Finding
from securetask.findings.repository import FindingRepository
from securetask.evidence.vault import EvidenceVault
from securetask.evidence.models import Evidence
from securetask.remediation.tracker import RemediationTracker
from securetask.remediation.workflow import RemediationTask
from securetask.compliance.repository import ComplianceRepository
from common.core import ValidationError
from securetask.utils.validation import ValidationError as SecureValidationError


class ReportType(str, Enum):
    """Types of security reports that can be generated."""
    
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_SUMMARY = "technical_summary"
    DETAILED_FINDINGS = "detailed_findings"
    COMPLIANCE_REPORT = "compliance_report"
    REMEDIATION_PLAN = "remediation_plan"
    EVIDENCE_REPORT = "evidence_report"
    STATUS_UPDATE = "status_update"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Output formats for generated reports."""
    
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


class ReportSection:
    """Defines a section within a report template."""
    
    def __init__(
        self,
        name: str,
        title: str,
        template: str,
        audience_level: RedactionLevel = RedactionLevel.NONE,
        required: bool = True
    ):
        """
        Initialize a report section.
        
        Args:
            name: Internal name for the section
            title: Display title for the section
            template: Jinja2 template for rendering the section
            audience_level: Minimum audience level required to include this section
            required: Whether this section is required
        """
        self.name = name
        self.title = title
        self.template = template
        self.audience_level = audience_level
        self.required = required


class ReportTemplate:
    """Defines structure and settings for a report type."""
    
    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        sections: List[ReportSection],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a report template.
        
        Args:
            name: Internal name for the template
            title: Display title for the template
            description: Description of the template
            sections: List of sections in the template
            metadata: Optional metadata for the template
        """
        self.name = name
        self.title = title
        self.description = description
        self.sections = sections
        self.metadata = metadata or {}


class Report:
    """
    Represents a generated security report.
    
    Stores report content, metadata, and provides methods for
    rendering and serializing the report.
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        type: ReportType,
        content: Dict[str, Any],
        generated_at: datetime,
        generated_by: str,
        redaction_level: RedactionLevel,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a report.
        
        Args:
            id: Unique identifier for the report
            title: Title of the report
            type: Type of report
            content: Report content organized by sections
            generated_at: Timestamp when the report was generated
            generated_by: ID of the user who generated the report
            redaction_level: Redaction level applied to the report
            metadata: Optional additional metadata
        """
        self.id = id
        self.title = title
        self.type = type
        self.content = content
        self.generated_at = generated_at
        self.generated_by = generated_by
        self.redaction_level = redaction_level
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the report to a dictionary.
        
        Returns:
            Dictionary representation of the report
        """
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value if isinstance(self.type, ReportType) else self.type,
            "content": self.content,
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
            "redaction_level": self.redaction_level.value if isinstance(self.redaction_level, RedactionLevel) else self.redaction_level,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """
        Convert the report to a JSON string.
        
        Returns:
            JSON string representation of the report
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """
        Create a report from a dictionary.
        
        Args:
            data: Dictionary representation of a report
            
        Returns:
            Report instance
        """
        # Parse datetime from string
        generated_at = datetime.fromisoformat(data["generated_at"]) if isinstance(data["generated_at"], str) else data["generated_at"]
        
        # Parse enums from strings
        report_type = ReportType(data["type"]) if isinstance(data["type"], str) else data["type"]
        redaction_level = RedactionLevel(data["redaction_level"]) if isinstance(data["redaction_level"], str) else data["redaction_level"]
        
        return cls(
            id=data["id"],
            title=data["title"],
            type=report_type,
            content=data["content"],
            generated_at=generated_at,
            generated_by=data["generated_by"],
            redaction_level=redaction_level,
            metadata=data.get("metadata", {})
        )


class ReportGenerator:
    """
    Generator for security reports with redaction capabilities.
    
    Creates different types of reports about security findings,
    remediation status, and compliance with appropriate redaction
    based on the intended audience.
    """
    
    def __init__(
        self,
        findings_repo: FindingRepository,
        evidence_vault: EvidenceVault,
        remediation_tracker: RemediationTracker,
        compliance_repo: ComplianceRepository,
        templates_dir: Optional[str] = None
    ):
        """
        Initialize the report generator.
        
        Args:
            findings_repo: Repository for security findings
            evidence_vault: Vault for evidence files
            remediation_tracker: Tracker for remediation tasks
            compliance_repo: Repository for compliance frameworks
            templates_dir: Optional directory for report templates
        """
        self.findings_repo = findings_repo
        self.evidence_vault = evidence_vault
        self.remediation_tracker = remediation_tracker
        self.compliance_repo = compliance_repo
        
        # Initialize redaction engine
        self.redaction_engine = RedactionEngine()
        
        # Set up Jinja2 environment for templates
        if templates_dir and os.path.exists(templates_dir):
            self.template_loader = jinja2.FileSystemLoader(templates_dir)
        else:
            # Use default templates
            self.default_templates = self._get_default_templates()
            self.template_loader = jinja2.DictLoader(self.default_templates)

        self.jinja_env = jinja2.Environment(
            loader=self.template_loader,
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Initialize templates with empty context
        self.templates = self._initialize_templates()
    
    def generate_report(
        self,
        report_type: Union[ReportType, str],
        title: str,
        findings: List[str],
        audience_level: Union[RedactionLevel, str] = RedactionLevel.MEDIUM,
        report_format: Union[ReportFormat, str] = ReportFormat.JSON,
        generated_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Report:
        """
        Generate a report for the specified findings.
        
        Args:
            report_type: Type of report to generate
            title: Title for the report
            findings: List of finding IDs to include
            audience_level: Redaction level based on audience
            report_format: Output format for the report
            generated_by: ID of the user generating the report
            metadata: Optional additional metadata
            
        Returns:
            Generated report
            
        Raises:
            ValidationError: If validation fails
            ValueError: If report type is not supported
        """
        start_time = time.time()
        
        # Convert string enums to enum types
        if isinstance(report_type, str):
            report_type = ReportType(report_type)
            
        if isinstance(audience_level, str):
            audience_level = RedactionLevel(audience_level)
            
        if isinstance(report_format, str):
            report_format = ReportFormat(report_format)
        
        # Get template for the report type
        template = self._get_template_for_type(report_type)
        if not template:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        # Collect data for the report
        finding_objects = []
        for finding_id in findings:
            try:
                finding = self.findings_repo.get(finding_id)
                finding_objects.append(finding)
            except Exception as e:
                print(f"Warning: Could not load finding {finding_id}: {str(e)}")
        
        # Sort findings by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        finding_objects.sort(key=lambda f: severity_order.get(f.severity, 999))
        
        # Generate content for each section
        content = {}
        
        for section in template.sections:
            # Skip sections that are too detailed for the audience level
            section_level = self._get_redaction_level_value(section.audience_level)
            audience_level_value = self._get_redaction_level_value(audience_level)
            
            if section_level > audience_level_value and not section.required:
                continue
                
            # Prepare context for the template
            context = {
                "findings": finding_objects,
                "title": title,
                "generated_at": datetime.now(),
                "metadata": metadata or {},
                # Add helper functions
                "get_evidence": self._get_evidence_for_template,
                "get_remediation": self._get_remediation_for_template,
                "get_compliance": self._get_compliance_for_template,
                "format_date": lambda d: d.strftime("%Y-%m-%d %H:%M:%S") if d else "N/A"
            }
            
            # Render the section
            jinja_template = self.jinja_env.from_string(section.template)
            section_content = jinja_template.render(**context)
            
            # Apply redaction
            redacted_content = self.redaction_engine.redact_text(section_content, audience_level)
            
            # Add to content
            content[section.name] = {
                "title": section.title,
                "content": redacted_content
            }
        
        # Create the report
        report = Report(
            id=str(uuid.uuid4()),
            title=title,
            type=report_type,
            content=content,
            generated_at=datetime.now(),
            generated_by=generated_by,
            redaction_level=audience_level,
            metadata=metadata
        )
        
        execution_time = time.time() - start_time
        if execution_time > 30.0 and len(finding_objects) > 500:  # 30 seconds for 500+ findings
            print(f"Warning: Report generation took {execution_time:.2f}s for {len(finding_objects)} findings")
            
        return report
    
    def render_report(
        self,
        report: Report,
        output_format: Union[ReportFormat, str] = ReportFormat.JSON
    ) -> str:
        """
        Render a report in the specified format.
        
        Args:
            report: Report to render
            output_format: Format to render in
            
        Returns:
            Rendered report as a string
            
        Raises:
            ValueError: If output format is not supported
        """
        # Convert string to enum if needed
        if isinstance(output_format, str):
            output_format = ReportFormat(output_format)
            
        if output_format == ReportFormat.JSON:
            return report.to_json()
            
        elif output_format == ReportFormat.MARKDOWN:
            return self._render_markdown(report)
            
        elif output_format == ReportFormat.HTML:
            return self._render_html(report)
            
        elif output_format == ReportFormat.TEXT:
            return self._render_text(report)
            
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def save_report(
        self,
        report: Report,
        output_file: str,
        output_format: Union[ReportFormat, str] = ReportFormat.JSON
    ) -> None:
        """
        Save a report to a file.
        
        Args:
            report: Report to save
            output_file: Path to save the report to
            output_format: Format to save in
            
        Raises:
            ValueError: If output format is not supported
            IOError: If file cannot be written
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Render the report
        rendered = self.render_report(report, output_format)
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(rendered)
    
    def _get_evidence_for_template(self, finding: Finding) -> List[Dict[str, Any]]:
        """
        Get evidence metadata for a finding, for use in templates.
        
        Args:
            finding: Finding to get evidence for
            
        Returns:
            List of evidence metadata dictionaries
        """
        evidence_list = []
        
        for evidence_id in finding.evidence_ids:
            try:
                evidence = self.evidence_vault.get_metadata(evidence_id)
                evidence_list.append({
                    "id": evidence.id,
                    "title": evidence.title,
                    "description": evidence.description,
                    "type": evidence.type.value if hasattr(evidence.type, "value") else evidence.type,
                    "uploaded_at": evidence.uploaded_date,
                    "uploaded_by": evidence.uploaded_by
                })
            except Exception:
                # Skip evidence that can't be loaded
                pass
                
        return evidence_list
    
    def _get_remediation_for_template(self, finding: Finding) -> Optional[Dict[str, Any]]:
        """
        Get remediation task for a finding, for use in templates.
        
        Args:
            finding: Finding to get remediation for
            
        Returns:
            Remediation task metadata or None
        """
        try:
            task = self.remediation_tracker.get_task_by_finding(finding.id)
            if task:
                return {
                    "id": task.id,
                    "title": task.title,
                    "state": task.state.value if hasattr(task.state, "value") else task.state,
                    "assigned_to": task.assigned_to,
                    "due_date": task.due_date,
                    "progress": task.progress_percentage
                }
        except Exception:
            # Return None if task can't be loaded
            pass
            
        return None
    
    def _get_compliance_for_template(self, finding: Finding) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get compliance controls for a finding, for use in templates.
        
        Args:
            finding: Finding to get compliance for
            
        Returns:
            Dictionary mapping framework IDs to lists of control metadata
        """
        result = {}
        
        try:
            controls_by_framework = self.compliance_repo.get_controls_for_finding(finding.id)
            
            for framework_id, controls in controls_by_framework.items():
                control_list = []
                
                for control in controls:
                    control_list.append({
                        "id": control.id,
                        "name": control.name,
                        "section": control.section,
                        "status": control.status.value if hasattr(control.status, "value") else control.status
                    })
                    
                if control_list:
                    result[framework_id] = control_list
        except Exception:
            # Return empty dict if compliance can't be loaded
            pass
            
        return result
    
    def _render_markdown(self, report: Report) -> str:
        """
        Render a report in Markdown format.
        
        Args:
            report: Report to render
            
        Returns:
            Markdown string
        """
        md_lines = []
        
        # Title
        md_lines.append(f"# {report.title}")
        md_lines.append("")
        
        # Metadata
        md_lines.append(f"**Report ID:** {report.id}")
        md_lines.append(f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"**Type:** {report.type.value if isinstance(report.type, ReportType) else report.type}")
        md_lines.append(f"**Audience Level:** {report.redaction_level.value if isinstance(report.redaction_level, RedactionLevel) else report.redaction_level}")
        md_lines.append("")
        
        # Content sections
        for section_name, section in report.content.items():
            md_lines.append(f"## {section['title']}")
            md_lines.append("")
            md_lines.append(section['content'])
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def _render_html(self, report: Report) -> str:
        """
        Render a report in HTML format.
        
        Args:
            report: Report to render
            
        Returns:
            HTML string
        """
        html_lines = []
        
        # Header
        html_lines.append("<!DOCTYPE html>")
        html_lines.append("<html>")
        html_lines.append("<head>")
        html_lines.append(f"<title>{report.title}</title>")
        html_lines.append("<style>")
        html_lines.append("body { font-family: Arial, sans-serif; margin: 40px; }")
        html_lines.append("h1 { color: #2c3e50; }")
        html_lines.append("h2 { color: #3498db; margin-top: 30px; }")
        html_lines.append(".metadata { color: #7f8c8d; font-size: 0.9em; margin-bottom: 30px; }")
        html_lines.append(".section { margin-bottom: 30px; }")
        html_lines.append("</style>")
        html_lines.append("</head>")
        html_lines.append("<body>")
        
        # Title
        html_lines.append(f"<h1>{report.title}</h1>")
        
        # Metadata
        html_lines.append("<div class=\"metadata\">")
        html_lines.append(f"<p><strong>Report ID:</strong> {report.id}</p>")
        html_lines.append(f"<p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html_lines.append(f"<p><strong>Type:</strong> {report.type.value if isinstance(report.type, ReportType) else report.type}</p>")
        html_lines.append(f"<p><strong>Audience Level:</strong> {report.redaction_level.value if isinstance(report.redaction_level, RedactionLevel) else report.redaction_level}</p>")
        html_lines.append("</div>")
        
        # Content sections
        for section_name, section in report.content.items():
            html_lines.append(f"<div class=\"section\">")
            html_lines.append(f"<h2>{section['title']}</h2>")
            
            # Convert Markdown to HTML for section content
            content_html = section['content']
            # In a real implementation, we would use a Markdown converter here
            
            html_lines.append(f"<div class=\"section-content\">{content_html}</div>")
            html_lines.append("</div>")
        
        # Footer
        html_lines.append("</body>")
        html_lines.append("</html>")
        
        return "\n".join(html_lines)
    
    def _render_text(self, report: Report) -> str:
        """
        Render a report in plain text format.
        
        Args:
            report: Report to render
            
        Returns:
            Plain text string
        """
        text_lines = []
        
        # Title
        text_lines.append(report.title)
        text_lines.append("=" * len(report.title))
        text_lines.append("")
        
        # Metadata
        text_lines.append(f"Report ID: {report.id}")
        text_lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        text_lines.append(f"Type: {report.type.value if isinstance(report.type, ReportType) else report.type}")
        text_lines.append(f"Audience Level: {report.redaction_level.value if isinstance(report.redaction_level, RedactionLevel) else report.redaction_level}")
        text_lines.append("")
        
        # Content sections
        for section_name, section in report.content.items():
            text_lines.append(section['title'])
            text_lines.append("-" * len(section['title']))
            text_lines.append("")
            text_lines.append(section['content'])
            text_lines.append("")
        
        return "\n".join(text_lines)
    
    def _initialize_templates(self) -> Dict[str, ReportTemplate]:
        """
        Initialize report templates.

        Returns:
            Dictionary mapping report types to templates
        """
        templates = {}

        # Executive Summary
        templates[ReportType.EXECUTIVE_SUMMARY] = ReportTemplate(
            name="executive_summary",
            title="Executive Summary",
            description="High-level summary of security findings for executives",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["executive_summary/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="findings_summary",
                    title="Findings Summary",
                    template=self.default_templates["executive_summary/findings_summary.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="recommendations",
                    title="Recommendations",
                    template=self.default_templates["executive_summary/recommendations.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                )
            ]
        )

        # Technical Summary
        templates[ReportType.TECHNICAL_SUMMARY] = ReportTemplate(
            name="technical_summary",
            title="Technical Summary",
            description="Technical summary of security findings",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["technical_summary/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="findings_summary",
                    title="Findings Summary",
                    template=self.default_templates["technical_summary/findings_summary.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="technical_details",
                    title="Technical Details",
                    template=self.default_templates["technical_summary/technical_details.md"],
                    audience_level=RedactionLevel.LOW,
                    required=False
                ),
                ReportSection(
                    name="recommendations",
                    title="Remediation Recommendations",
                    template=self.default_templates["technical_summary/recommendations.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                )
            ]
        )
        
        # Detailed Findings
        templates[ReportType.DETAILED_FINDINGS] = ReportTemplate(
            name="detailed_findings",
            title="Detailed Findings",
            description="Detailed description of all security findings",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["detailed_findings/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="findings",
                    title="Findings",
                    template=self.default_templates["detailed_findings/findings.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="technical_details",
                    title="Technical Details",
                    template=self.default_templates["detailed_findings/technical_details.md"],
                    audience_level=RedactionLevel.LOW,
                    required=False
                ),
                ReportSection(
                    name="exploitation",
                    title="Exploitation Details",
                    template=self.default_templates["detailed_findings/exploitation.md"],
                    audience_level=RedactionLevel.MEDIUM,
                    required=False
                ),
                ReportSection(
                    name="remediation",
                    title="Remediation",
                    template=self.default_templates["detailed_findings/remediation.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                )
            ]
        )
        
        # Compliance Report
        templates[ReportType.COMPLIANCE_REPORT] = ReportTemplate(
            name="compliance_report",
            title="Compliance Report",
            description="Report on compliance status and gaps",
            sections=[
                ReportSection(
                    name="overview",
                    title="Compliance Overview",
                    template=self.default_templates["compliance_report/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="compliance_status",
                    title="Compliance Status",
                    template=self.default_templates["compliance_report/compliance_status.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="compliance_gaps",
                    title="Compliance Gaps",
                    template=self.default_templates["compliance_report/compliance_gaps.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="findings_mapping",
                    title="Findings to Compliance Mapping",
                    template=self.default_templates["compliance_report/findings_mapping.md"],
                    audience_level=RedactionLevel.LOW,
                    required=False
                ),
                ReportSection(
                    name="remediation_plan",
                    title="Remediation Plan",
                    template=self.default_templates["compliance_report/remediation_plan.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                )
            ]
        )
        
        # Remediation Plan
        templates[ReportType.REMEDIATION_PLAN] = ReportTemplate(
            name="remediation_plan",
            title="Remediation Plan",
            description="Plan for remediating security findings",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["remediation_plan/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="remediation_tasks",
                    title="Remediation Tasks",
                    template=self.default_templates["remediation_plan/remediation_tasks.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="timeline",
                    title="Timeline",
                    template=self.default_templates["remediation_plan/timeline.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="technical_details",
                    title="Technical Details",
                    template=self.default_templates["remediation_plan/technical_details.md"],
                    audience_level=RedactionLevel.LOW,
                    required=False
                )
            ]
        )
        
        # Evidence Report
        templates[ReportType.EVIDENCE_REPORT] = ReportTemplate(
            name="evidence_report",
            title="Evidence Report",
            description="Detailed report of evidence collected during assessment",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["evidence_report/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="evidence",
                    title="Evidence Details",
                    template=self.default_templates["evidence_report/evidence.md"],
                    audience_level=RedactionLevel.LOW,
                    required=True
                )
            ]
        )
        
        # Status Update
        templates[ReportType.STATUS_UPDATE] = ReportTemplate(
            name="status_update",
            title="Status Update",
            description="Current status of findings and remediation efforts",
            sections=[
                ReportSection(
                    name="overview",
                    title="Overview",
                    template=self.default_templates["status_update/overview.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                ),
                ReportSection(
                    name="findings_status",
                    title="Findings Status",
                    template=self.default_templates["status_update/findings_status.md"],
                    audience_level=RedactionLevel.NONE,
                    required=True
                )
            ]
        )
        
        return templates
    
    def _get_template_for_type(self, report_type: ReportType) -> Optional[ReportTemplate]:
        """
        Get the template for a report type.
        
        Args:
            report_type: Type of report
            
        Returns:
            Template for the report type or None if not found
        """
        return self.templates.get(report_type)
    
    def _get_redaction_level_value(self, level: RedactionLevel) -> int:
        """
        Get numeric value for a redaction level for comparison.
        
        Args:
            level: Redaction level
            
        Returns:
            Numeric value
        """
        level_values = {
            RedactionLevel.NONE: 0,
            RedactionLevel.LOW: 1,
            RedactionLevel.MEDIUM: 2,
            RedactionLevel.HIGH: 3,
            RedactionLevel.MAXIMUM: 4
        }
        
        return level_values.get(level, 0)
    
    def _get_default_templates(self) -> Dict[str, str]:
        """
        Get default templates for reports.
        
        Returns:
            Dictionary mapping template names to template content
        """
        templates = {}
        
        # Executive Summary templates
        templates["executive_summary/overview.md"] = """
# Executive Summary

This report summarizes the security assessment conducted on {{ metadata.get('target', 'the target system') }} from {{ metadata.get('start_date', 'N/A') }} to {{ metadata.get('end_date', 'N/A') }}.

## Summary of Findings

{% set critical_count = findings|selectattr('severity', 'eq', 'critical')|list|length %}
{% set high_count = findings|selectattr('severity', 'eq', 'high')|list|length %}
{% set medium_count = findings|selectattr('severity', 'eq', 'medium')|list|length %}
{% set low_count = findings|selectattr('severity', 'eq', 'low')|list|length %}
{% set info_count = findings|selectattr('severity', 'eq', 'info')|list|length %}

A total of {{ findings|length }} security findings were identified:

* Critical: {{ critical_count }}
* High: {{ high_count }}
* Medium: {{ medium_count }}
* Low: {{ low_count }}
* Informational: {{ info_count }}
"""
        
        templates["executive_summary/findings_summary.md"] = """
## Key Findings

{% for finding in findings if finding.severity in ['critical', 'high'] %}
### {{ finding.title }}

* **Severity**: {{ finding.severity|upper }}
{% if finding.cvss_score %}* **CVSS Score**: {{ finding.cvss_score }}{% endif %}
* **Summary**: {{ finding.description }}
{% if get_remediation(finding) %}* **Status**: {{ get_remediation(finding).state }}{% endif %}

{% endfor %}
"""
        
        templates["executive_summary/recommendations.md"] = """
## Recommendations

1. Address all Critical and High severity findings as soon as possible
2. Implement a regular security assessment program
3. Establish clear remediation processes and timelines
4. Verify remediation effectiveness through retesting
"""
        
        # Technical Summary templates
        templates["technical_summary/overview.md"] = """
# Technical Summary

This report provides a technical summary of the security assessment conducted on {{ metadata.get('target', 'the target system') }}.

## Assessment Scope

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Time Period**: {{ metadata.get('start_date', 'N/A') }} to {{ metadata.get('end_date', 'N/A') }}
* **Assessment Type**: {{ metadata.get('assessment_type', 'Security Assessment') }}
* **Methodology**: {{ metadata.get('methodology', 'Standard security testing methodology') }}
"""
        
        templates["technical_summary/findings_summary.md"] = """
## Findings Summary

{% set critical_count = findings|selectattr('severity', 'eq', 'critical')|list|length %}
{% set high_count = findings|selectattr('severity', 'eq', 'high')|list|length %}
{% set medium_count = findings|selectattr('severity', 'eq', 'medium')|list|length %}
{% set low_count = findings|selectattr('severity', 'eq', 'low')|list|length %}
{% set info_count = findings|selectattr('severity', 'eq', 'info')|list|length %}

A total of {{ findings|length }} security findings were identified:

* Critical: {{ critical_count }}
* High: {{ high_count }}
* Medium: {{ medium_count }}
* Low: {{ low_count }}
* Informational: {{ info_count }}

### Finding Categories

{% set categories = {} %}
{% for finding in findings %}
    {% set category = finding.tags[0] if finding.tags else 'Uncategorized' %}
    {% if category in categories %}
        {% set _ = categories.update({category: categories[category] + 1}) %}
    {% else %}
        {% set _ = categories.update({category: 1}) %}
    {% endif %}
{% endfor %}

{% for category, count in categories.items() %}
* {{ category }}: {{ count }}
{% endfor %}
"""
        
        templates["technical_summary/technical_details.md"] = """
## Technical Details

{% for finding in findings %}
### {{ finding.title }}

* **ID**: {{ finding.id }}
* **Severity**: {{ finding.severity|upper }}
{% if finding.cvss_score %}* **CVSS Score**: {{ finding.cvss_score }} ({{ finding.cvss_vector }}){% endif %}
* **Affected Systems**: {{ finding.affected_systems|join(', ') }}
* **Description**: {{ finding.description }}

{% if get_evidence(finding) %}
#### Evidence

{% for evidence in get_evidence(finding) %}
* {{ evidence.title }} ({{ evidence.type }})
{% endfor %}
{% endif %}

{% endfor %}
"""
        
        templates["technical_summary/recommendations.md"] = """
## Remediation Recommendations

{% for finding in findings %}
### {{ finding.title }} ({{ finding.severity|upper }})

{% if finding.remediation_plan %}
{{ finding.remediation_plan }}
{% else %}
No specific remediation plan has been defined for this finding.
{% endif %}

{% if get_remediation(finding) %}
**Current Status**: {{ get_remediation(finding).state }}
{% if get_remediation(finding).due_date %}**Due Date**: {{ format_date(get_remediation(finding).due_date) }}{% endif %}
{% if get_remediation(finding).assigned_to %}**Assigned To**: {{ get_remediation(finding).assigned_to }}{% endif %}
{% endif %}

{% endfor %}
"""
        
        # Detailed Findings templates
        templates["detailed_findings/overview.md"] = """
# Detailed Findings Report

This report provides detailed information about security findings identified during the assessment of {{ metadata.get('target', 'the target system') }}.

## Assessment Information

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Time Period**: {{ metadata.get('start_date', 'N/A') }} to {{ metadata.get('end_date', 'N/A') }}
* **Assessment Type**: {{ metadata.get('assessment_type', 'Security Assessment') }}
* **Assessor**: {{ metadata.get('assessor', 'N/A') }}
"""
        
        templates["detailed_findings/findings.md"] = """
## Detailed Findings

{% for finding in findings %}
### {{ finding.severity|upper }}: {{ finding.title }}

* **ID**: {{ finding.id }}
* **Severity**: {{ finding.severity|upper }}
{% if finding.cvss_score %}* **CVSS Score**: {{ finding.cvss_score }} ({{ finding.cvss_vector }}){% endif %}
* **Affected Systems**: {{ finding.affected_systems|join(', ') }}
* **Discovery Date**: {{ format_date(finding.discovered_date) }}
* **Status**: {{ finding.status }}

#### Description

{{ finding.description }}

{% if finding.references %}
#### References

{% for ref in finding.references %}
* {{ ref }}
{% endfor %}
{% endif %}

{% endfor %}
"""
        
        templates["detailed_findings/technical_details.md"] = """
## Technical Details

{% for finding in findings %}
### {{ finding.title }}

#### Detailed Technical Description

{{ finding.description }}

{% if get_evidence(finding) %}
#### Evidence

{% for evidence in get_evidence(finding) %}
* **{{ evidence.title }}** ({{ evidence.type }})
  * Uploaded: {{ format_date(evidence.uploaded_at) }}
  * Description: {{ evidence.description }}
{% endfor %}
{% endif %}

{% endfor %}
"""
        
        templates["detailed_findings/exploitation.md"] = """
## Exploitation Details

{% for finding in findings %}
### {{ finding.title }}

{% set exploit_evidence = [] %}
{% for evidence in get_evidence(finding) %}
    {% if evidence.type == 'exploit' %}
        {% set _ = exploit_evidence.append(evidence) %}
    {% endif %}
{% endfor %}

{% if exploit_evidence %}
#### Exploit Information

{% for evidence in exploit_evidence %}
* **{{ evidence.title }}**
  * Description: {{ evidence.description }}
  * Uploaded: {{ format_date(evidence.uploaded_at) }}
{% endfor %}
{% else %}
No specific exploitation details are available for this finding.
{% endif %}

{% endfor %}
"""
        
        templates["detailed_findings/remediation.md"] = """
## Remediation Details

{% for finding in findings %}
### {{ finding.title }} ({{ finding.severity|upper }})

{% if finding.remediation_plan %}
#### Recommended Fix

{{ finding.remediation_plan }}
{% endif %}

{% if get_remediation(finding) %}
#### Remediation Status

* **Status**: {{ get_remediation(finding).state }}
{% if get_remediation(finding).due_date %}* **Due Date**: {{ format_date(get_remediation(finding).due_date) }}{% endif %}
{% if get_remediation(finding).assigned_to %}* **Assigned To**: {{ get_remediation(finding).assigned_to }}{% endif %}
* **Progress**: {{ get_remediation(finding).progress }}%
{% endif %}

{% endfor %}
"""
        
        # Compliance Report templates
        templates["compliance_report/overview.md"] = """
# Compliance Report

This report provides an assessment of the compliance status of {{ metadata.get('target', 'the target system') }} against relevant regulatory and security frameworks.

## Assessment Overview

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Assessment Date**: {{ format_date(generated_at) }}
* **Frameworks Assessed**: {{ metadata.get('frameworks', 'N/A') }}
"""
        
        templates["compliance_report/compliance_status.md"] = """
## Compliance Status Summary

{% set compliance_data = {} %}
{% for finding in findings %}
    {% set controls = get_compliance(finding) %}
    {% for framework_id, framework_controls in controls.items() %}
        {% if framework_id not in compliance_data %}
            {% set _ = compliance_data.update({framework_id: {'compliant': 0, 'non_compliant': 0, 'partially_compliant': 0, 'unknown': 0}}) %}
        {% endif %}
        {% for control in framework_controls %}
            {% if control.status == 'compliant' %}
                {% set _ = compliance_data[framework_id].update({'compliant': compliance_data[framework_id]['compliant'] + 1}) %}
            {% elif control.status == 'non_compliant' %}
                {% set _ = compliance_data[framework_id].update({'non_compliant': compliance_data[framework_id]['non_compliant'] + 1}) %}
            {% elif control.status == 'partially_compliant' %}
                {% set _ = compliance_data[framework_id].update({'partially_compliant': compliance_data[framework_id]['partially_compliant'] + 1}) %}
            {% else %}
                {% set _ = compliance_data[framework_id].update({'unknown': compliance_data[framework_id]['unknown'] + 1}) %}
            {% endif %}
        {% endfor %}
    {% endfor %}
{% endfor %}

{% for framework_id, counts in compliance_data.items() %}
### {{ framework_id }}

* **Compliant**: {{ counts.compliant }}
* **Non-Compliant**: {{ counts.non_compliant }}
* **Partially Compliant**: {{ counts.partially_compliant }}
* **Unknown**: {{ counts.unknown }}
* **Total Controls Assessed**: {{ counts.compliant + counts.non_compliant + counts.partially_compliant + counts.unknown }}
{% endfor %}
"""
        
        templates["compliance_report/compliance_gaps.md"] = """
## Compliance Gaps

{% for finding in findings %}
    {% set controls = get_compliance(finding) %}
    {% if controls %}
        {% for framework_id, framework_controls in controls.items() %}
            {% for control in framework_controls %}
                {% if control.status == 'non_compliant' %}
### {{ framework_id }}: {{ control.id }} - {{ control.name }}

* **Finding**: {{ finding.title }}
* **Severity**: {{ finding.severity|upper }}
* **Description**: {{ finding.description }}

{% if finding.remediation_plan %}
#### Remediation Plan

{{ finding.remediation_plan }}
{% endif %}
                {% endif %}
            {% endfor %}
        {% endfor %}
    {% endif %}
{% endfor %}
"""
        
        templates["compliance_report/findings_mapping.md"] = """
## Findings to Compliance Mapping

{% for finding in findings %}
### {{ finding.title }} ({{ finding.severity|upper }})

{% set controls = get_compliance(finding) %}
{% if controls %}
#### Affected Compliance Controls

{% for framework_id, framework_controls in controls.items() %}
##### {{ framework_id }}

{% for control in framework_controls %}
* **{{ control.id }}**: {{ control.name }} (Section {{ control.section }})
{% endfor %}
{% endfor %}
{% else %}
No compliance mappings found for this finding.
{% endif %}

{% endfor %}
"""
        
        templates["compliance_report/remediation_plan.md"] = """
## Compliance Remediation Plan

{% set non_compliant_controls = {} %}
{% for finding in findings %}
    {% set controls = get_compliance(finding) %}
    {% for framework_id, framework_controls in controls.items() %}
        {% for control in framework_controls %}
            {% if control.status == 'non_compliant' %}
                {% if framework_id not in non_compliant_controls %}
                    {% set _ = non_compliant_controls.update({framework_id: []}) %}
                {% endif %}
                {% set _ = non_compliant_controls[framework_id].append({'control': control, 'finding': finding}) %}
            {% endif %}
        {% endfor %}
    {% endfor %}
{% endfor %}

{% for framework_id, items in non_compliant_controls.items() %}
### {{ framework_id }}

{% for item in items %}
#### {{ item.control.id }}: {{ item.control.name }}

* **Finding**: {{ item.finding.title }}
* **Severity**: {{ item.finding.severity|upper }}

{% if item.finding.remediation_plan %}
**Remediation Plan**:

{{ item.finding.remediation_plan }}
{% endif %}

{% if get_remediation(item.finding) %}
**Status**: {{ get_remediation(item.finding).state }}
{% if get_remediation(item.finding).due_date %}**Due Date**: {{ format_date(get_remediation(item.finding).due_date) }}{% endif %}
{% endif %}

{% endfor %}
{% endfor %}
"""
        
        # Remediation Plan templates
        templates["remediation_plan/overview.md"] = """
# Remediation Plan

This document outlines the plan for addressing security findings identified during the assessment of {{ metadata.get('target', 'the target system') }}.

## Overview

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Assessment Date**: {{ metadata.get('assessment_date', 'N/A') }}
* **Remediation Timeline**: {{ metadata.get('remediation_timeline', 'N/A') }}
* **Total Findings**: {{ findings|length }}
"""
        
        templates["remediation_plan/remediation_tasks.md"] = """
## Remediation Tasks

{% for finding in findings|sort(attribute='severity') %}
### {{ finding.severity|upper }}: {{ finding.title }}

* **Finding ID**: {{ finding.id }}
* **Severity**: {{ finding.severity|upper }}
{% if finding.cvss_score %}* **CVSS Score**: {{ finding.cvss_score }}{% endif %}
* **Affected Systems**: {{ finding.affected_systems|join(', ') }}

#### Recommended Actions

{% if finding.remediation_plan %}
{{ finding.remediation_plan }}
{% else %}
No specific remediation plan has been defined for this finding.
{% endif %}

{% if get_remediation(finding) %}
#### Current Status

* **Status**: {{ get_remediation(finding).state }}
{% if get_remediation(finding).assigned_to %}* **Assigned To**: {{ get_remediation(finding).assigned_to }}{% endif %}
{% if get_remediation(finding).due_date %}* **Due Date**: {{ format_date(get_remediation(finding).due_date) }}{% endif %}
* **Progress**: {{ get_remediation(finding).progress }}%
{% endif %}

{% endfor %}
"""
        
        templates["remediation_plan/timeline.md"] = """
## Remediation Timeline

{% set severity_priority = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4, 'info': 5} %}
{% set findings_with_remediation = [] %}
{% for finding in findings %}
    {% set remediation = get_remediation(finding) %}
    {% if remediation and remediation.due_date %}
        {% set _ = findings_with_remediation.append({'finding': finding, 'remediation': remediation, 'priority': severity_priority.get(finding.severity, 999)}) %}
    {% endif %}
{% endfor %}

{% if findings_with_remediation %}
| Due Date | Finding | Severity | Status | Assigned To |
|----------|---------|----------|--------|------------|
{% for item in findings_with_remediation|sort(attribute='remediation.due_date') %}
| {{ format_date(item.remediation.due_date) }} | {{ item.finding.title }} | {{ item.finding.severity|upper }} | {{ item.remediation.state }} | {{ item.remediation.assigned_to if item.remediation.assigned_to else 'Unassigned' }} |
{% endfor %}
{% else %}
No remediation timeline information is currently available.
{% endif %}
"""
        
        templates["remediation_plan/technical_details.md"] = """
## Technical Details

This section provides additional technical information to assist with remediation.

{% for finding in findings %}
### {{ finding.title }}

* **ID**: {{ finding.id }}
* **Severity**: {{ finding.severity|upper }}
{% if finding.cvss_score %}* **CVSS Score**: {{ finding.cvss_score }} ({{ finding.cvss_vector }}){% endif %}
* **Affected Systems**: {{ finding.affected_systems|join(', ') }}
* **Description**: {{ finding.description }}

{% if finding.references %}
#### References

{% for ref in finding.references %}
* {{ ref }}
{% endfor %}
{% endif %}

{% if get_evidence(finding) %}
#### Supporting Evidence

{% for evidence in get_evidence(finding) %}
* **{{ evidence.title }}** ({{ evidence.type }})
  * Description: {{ evidence.description }}
{% endfor %}
{% endif %}

{% endfor %}
"""
        
        # Evidence Report templates
        templates["evidence_report/overview.md"] = """
# Evidence Report

This report provides detailed information about the evidence collected during the security assessment of {{ metadata.get('target', 'the target system') }}.

## Assessment Information

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Time Period**: {{ metadata.get('start_date', 'N/A') }} to {{ metadata.get('end_date', 'N/A') }}
* **Assessment Type**: {{ metadata.get('assessment_type', 'Security Assessment') }}
* **Assessor**: {{ metadata.get('assessor', 'N/A') }}
"""

        templates["evidence_report/evidence.md"] = """
## Evidence Details

{% for finding in findings %}
### {{ finding.severity|upper }}: {{ finding.title }}

{% if get_evidence(finding) %}
#### Evidence Items

{% for evidence in get_evidence(finding) %}
##### {{ evidence.title }} ({{ evidence.type }})

* **ID**: {{ evidence.id }}
* **Description**: {{ evidence.description }}
* **Uploaded**: {{ format_date(evidence.uploaded_at) }}
* **Uploaded By**: {{ evidence.uploaded_by }}
* **Type**: {{ evidence.type }}

{% endfor %}
{% else %}
No evidence items attached to this finding.
{% endif %}

{% endfor %}
"""

        # Status Update templates
        templates["status_update/overview.md"] = """
# Status Update Report

This report provides an update on the current status of security findings and remediation efforts for {{ metadata.get('target', 'the target system') }}.

## Overview

* **Target**: {{ metadata.get('target', 'N/A') }}
* **Report Date**: {{ format_date(generated_at) }}
* **Previous Report**: {{ metadata.get('previous_report_date', 'N/A') }}

## Summary

{% set total = findings|length %}
{% set open = findings|selectattr('status', 'eq', 'open')|list|length %}
{% set in_progress = findings|selectattr('status', 'eq', 'in_progress')|list|length %}
{% set remediated = findings|selectattr('status', 'eq', 'remediated')|list|length %}
{% set closed = findings|selectattr('status', 'eq', 'closed')|list|length %}

* **Total Findings**: {{ total }}
* **Open**: {{ open }} ({{ (open / total * 100)|round(1) if total > 0 else 0 }}%)
* **In Progress**: {{ in_progress }} ({{ (in_progress / total * 100)|round(1) if total > 0 else 0 }}%)
* **Remediated**: {{ remediated }} ({{ (remediated / total * 100)|round(1) if total > 0 else 0 }}%)
* **Closed**: {{ closed }} ({{ (closed / total * 100)|round(1) if total > 0 else 0 }}%)
"""

        templates["status_update/findings_status.md"] = """
## Finding Status Details

| Finding | Severity | Status | Remediation Progress | Due Date |
|---------|----------|--------|---------------------|----------|
{% for finding in findings %}
{% set remediation = get_remediation(finding) %}
| {{ finding.title }} | {{ finding.severity|upper }} | {{ finding.status }} | {% if remediation %}{{ remediation.progress }}%{% else %}N/A{% endif %} | {% if remediation and remediation.due_date %}{{ format_date(remediation.due_date) }}{% else %}N/A{% endif %} |
{% endfor %}

## Recent Updates

{% for finding in findings %}
{% if finding.status == 'in_progress' or finding.status == 'remediated' %}
### {{ finding.title }}

* **Current Status**: {{ finding.status|upper }}
{% set remediation = get_remediation(finding) %}
{% if remediation %}
* **Assigned To**: {{ remediation.assigned_to if remediation.assigned_to else 'Unassigned' }}
* **Progress**: {{ remediation.progress }}%
{% if remediation.due_date %}* **Due Date**: {{ format_date(remediation.due_date) }}{% endif %}
{% endif %}

{% if finding.status == 'remediated' %}
#### Resolution
{{ finding.resolution if finding.resolution else 'No resolution details provided.' }}
{% endif %}

{% endif %}
{% endfor %}
"""
        
        return templates