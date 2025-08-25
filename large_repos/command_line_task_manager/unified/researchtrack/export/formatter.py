from typing import Dict, List, Optional, Union, Any

from .models import (
    CitationBlock,
    CodeBlock,
    Document,
    EquationBlock,
    ImageBlock,
    JournalFormat,
    Section,
    TableBlock,
    TextBlock,
)


class ExportFormatter:
    """Utility class for formatting academic documents for export."""

    def format_document(self, document: Document) -> str:
        """
        Format a document for export based on its journal format.

        Args:
            document: The document to format

        Returns:
            str: The formatted document as markdown
        """
        # Build the document parts
        parts = []

        # Title
        parts.append(f"# {document.title}")
        parts.append("")

        # Authors
        if document.authors:
            if document.format == JournalFormat.NATURE:
                parts.append(f"Authors: {', '.join(document.authors)}")
            else:
                parts.append(f"By {', '.join(document.authors)}")

        # Affiliations
        if document.affiliations:
            parts.append(f"Affiliations: {', '.join(document.affiliations)}")

        # Email
        if document.corresponding_email:
            parts.append(f"Corresponding email: {document.corresponding_email}")

        # Keywords
        if document.keywords:
            parts.append(f"Keywords: {', '.join(document.keywords)}")

        parts.append("")

        # Format sections
        for section in document.sections:
            parts.append(self.format_section(section))
            parts.append("")

        return "\n".join(parts)

    def format_section(self, section: Section) -> str:
        """
        Format a section into markdown.

        Args:
            section: The section to format

        Returns:
            str: The section formatted as markdown
        """
        parts = []

        # Section title
        parts.append(f"## {section.title}")
        parts.append("")

        # Format each content block
        for block in section.content_blocks:
            if isinstance(block, TextBlock):
                parts.append(self.format_text_block(block))
            elif isinstance(block, ImageBlock):
                parts.append(self.format_image_block(block))
            elif isinstance(block, TableBlock):
                parts.append(self.format_table_block(block))
            elif isinstance(block, CodeBlock):
                parts.append(self.format_code_block(block))
            elif isinstance(block, EquationBlock):
                parts.append(self.format_equation_block(block))
            elif isinstance(block, CitationBlock):
                parts.append(self.format_citation_block(block))

            parts.append("")

        return "\n".join(parts)

    def format_text_block(self, block: TextBlock) -> str:
        """
        Format a text block into markdown.

        Args:
            block: The text block to format

        Returns:
            str: The text block as markdown
        """
        return block.content

    def format_image_block(self, block: ImageBlock) -> str:
        """
        Format an image block into markdown.

        Args:
            block: The image block to format

        Returns:
            str: The image block as markdown
        """
        caption = block.caption or ""
        return f"![{caption}]({block.path})"

    def format_table_block(self, block: TableBlock) -> str:
        """
        Format a table block into markdown.

        Args:
            block: The table block to format

        Returns:
            str: The table block as markdown
        """
        parts = []

        # Headers
        parts.append("| " + " | ".join(block.headers) + " |")
        parts.append("| " + " | ".join(["---"] * len(block.headers)) + " |")

        # Rows
        for row in block.data:
            parts.append("| " + " | ".join(row) + " |")

        # Caption
        if block.caption:
            parts.append("")
            parts.append(f"Table: {block.caption}")

        return "\n".join(parts)

    def format_code_block(self, block: CodeBlock) -> str:
        """
        Format a code block into markdown.

        Args:
            block: The code block to format

        Returns:
            str: The code block as markdown
        """
        return f"```{block.language}\n{block.code}\n```"

    def format_equation_block(self, block: EquationBlock) -> str:
        """
        Format an equation block into markdown.

        Args:
            block: The equation block to format

        Returns:
            str: The equation block as markdown
        """
        return f"${block.equation}$"

    def format_citation_block(self, block: CitationBlock) -> str:
        """
        Format a citation block into markdown.

        Args:
            block: The citation block to format

        Returns:
            str: The citation block as markdown
        """
        citations = "".join([f"[{ref_id}]" for ref_id in block.reference_ids])
        if block.context:
            return f"{block.context} {citations}"
        else:
            return citations

    def format_comparison_table(self, comparison_data: Dict[str, Dict[str, float]]) -> str:
        """
        Format a comparison table of multiple runs/experiments.

        Args:
            comparison_data: Dictionary mapping run/experiment names to metric values

        Returns:
            str: Markdown comparison table
        """
        if not comparison_data:
            return "No comparison data available."

        # Collect all metric names
        all_metrics = set()
        for run_data in comparison_data.values():
            all_metrics.update(run_data.keys())

        metrics = sorted(list(all_metrics))

        # Build table header
        header = ["Run/Experiment"]
        header.extend(metrics)

        table = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |",
        ]

        # Add rows
        for run_name, run_data in comparison_data.items():
            row = [run_name]

            for metric in metrics:
                if metric in run_data:
                    row.append(f"{run_data[metric]:.2f}")
                else:
                    row.append("-")

            table.append("| " + " | ".join(row) + " |")

        return "\n".join(table)