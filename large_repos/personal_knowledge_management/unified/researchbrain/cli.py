"""Command-line interface for ResearchBrain."""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import (
    CitationFormat, CollaboratorRole, EvidenceStrength, EvidenceType,
    ExperimentStatus, GrantStatus
)
from researchbrain.experiments.templates import list_templates


console = Console()


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="ResearchBrain - Knowledge Management for Academic Researchers")
    parser.add_argument("--data-dir", type=str, default="./data", help="Path to data directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize a new knowledge base")
    
    # Note commands
    note_parser = subparsers.add_parser("note", help="Manage research notes")
    note_subparsers = note_parser.add_subparsers(dest="note_command", help="Note command")
    
    # Create note
    create_note_parser = note_subparsers.add_parser("create", help="Create a new note")
    create_note_parser.add_argument("--title", "-t", required=True, help="Note title")
    create_note_parser.add_argument("--content", "-c", required=True, help="Note content")
    create_note_parser.add_argument("--tags", nargs="+", help="Tags for the note")
    create_note_parser.add_argument("--source", help="Source citation ID")
    create_note_parser.add_argument("--page", type=int, help="Page reference in the source")
    
    # List notes
    list_notes_parser = note_subparsers.add_parser("list", help="List notes")
    list_notes_parser.add_argument("--tag", help="Filter by tag")
    list_notes_parser.add_argument("--limit", type=int, default=10, help="Maximum number of notes to show")
    
    # View note
    view_note_parser = note_subparsers.add_parser("view", help="View a note")
    view_note_parser.add_argument("id", help="Note ID")
    
    # Update note
    update_note_parser = note_subparsers.add_parser("update", help="Update a note")
    update_note_parser.add_argument("id", help="Note ID")
    update_note_parser.add_argument("--title", "-t", help="New title")
    update_note_parser.add_argument("--content", "-c", help="New content")
    update_note_parser.add_argument("--tags", nargs="+", help="New tags")
    
    # Delete note
    delete_note_parser = note_subparsers.add_parser("delete", help="Delete a note")
    delete_note_parser.add_argument("id", help="Note ID")
    
    # Citation commands
    citation_parser = subparsers.add_parser("citation", help="Manage citations")
    citation_subparsers = citation_parser.add_subparsers(dest="citation_command", help="Citation command")
    
    # Import citation
    import_citation_parser = citation_subparsers.add_parser("import", help="Import a citation from a file")
    import_citation_parser.add_argument("file", help="Path to PDF, BibTeX, or RIS file")
    
    # Create citation
    create_citation_parser = citation_subparsers.add_parser("create", help="Create a new citation")
    create_citation_parser.add_argument("--title", "-t", required=True, help="Citation title")
    create_citation_parser.add_argument("--authors", "-a", required=True, nargs="+", help="Authors")
    create_citation_parser.add_argument("--year", "-y", type=int, help="Publication year")
    create_citation_parser.add_argument("--doi", "-d", help="DOI")
    create_citation_parser.add_argument("--journal", "-j", help="Journal or publication venue")
    
    # List citations
    list_citations_parser = citation_subparsers.add_parser("list", help="List citations")
    list_citations_parser.add_argument("--author", help="Filter by author")
    list_citations_parser.add_argument("--year", type=int, help="Filter by year")
    list_citations_parser.add_argument("--limit", type=int, default=10, help="Maximum number of citations to show")
    
    # View citation
    view_citation_parser = citation_subparsers.add_parser("view", help="View a citation")
    view_citation_parser.add_argument("id", help="Citation ID")
    view_citation_parser.add_argument("--format", choices=[f.value for f in CitationFormat], default=CitationFormat.APA.value, help="Citation format")
    
    # Link note to citation
    link_note_parser = citation_subparsers.add_parser("link", help="Link a note to a citation")
    link_note_parser.add_argument("note_id", help="Note ID")
    link_note_parser.add_argument("citation_id", help="Citation ID")
    link_note_parser.add_argument("--page", type=int, help="Page reference")
    
    # Research question commands
    question_parser = subparsers.add_parser("question", help="Manage research questions")
    question_subparsers = question_parser.add_subparsers(dest="question_command", help="Research question command")
    
    # Create question
    create_question_parser = question_subparsers.add_parser("create", help="Create a new research question")
    create_question_parser.add_argument("--question", "-q", required=True, help="Research question text")
    create_question_parser.add_argument("--description", "-d", help="Detailed description")
    create_question_parser.add_argument("--tags", nargs="+", help="Tags for the question")
    create_question_parser.add_argument("--priority", "-p", type=int, choices=range(11), default=5, help="Priority (0-10)")
    
    # List questions
    list_questions_parser = question_subparsers.add_parser("list", help="List research questions")
    list_questions_parser.add_argument("--status", choices=["open", "resolved", "abandoned"], help="Filter by status")
    list_questions_parser.add_argument("--priority", type=int, choices=range(11), help="Filter by minimum priority")
    
    # View question
    view_question_parser = question_subparsers.add_parser("view", help="View a research question")
    view_question_parser.add_argument("id", help="Question ID")
    
    # Add evidence
    add_evidence_parser = question_subparsers.add_parser("evidence", help="Add evidence to a research question")
    add_evidence_parser.add_argument("question_id", help="Question ID")
    add_evidence_parser.add_argument("note_id", help="Note ID containing the evidence")
    add_evidence_parser.add_argument("--type", "-t", choices=[t.value for t in EvidenceType], required=True, help="Evidence type")
    add_evidence_parser.add_argument("--strength", "-s", choices=[s.value for s in EvidenceStrength], required=True, help="Evidence strength")
    add_evidence_parser.add_argument("--description", "-d", help="Evidence description")
    
    # Experiment commands
    experiment_parser = subparsers.add_parser("experiment", help="Manage experiments")
    experiment_subparsers = experiment_parser.add_subparsers(dest="experiment_command", help="Experiment command")
    
    # Create experiment
    create_experiment_parser = experiment_subparsers.add_parser("create", help="Create a new experiment")
    create_experiment_parser.add_argument("--title", "-t", required=True, help="Experiment title")
    create_experiment_parser.add_argument("--hypothesis", "-hyp", required=True, help="Hypothesis being tested")
    create_experiment_parser.add_argument("--methodology", "-m", required=True, help="Experimental methodology")
    create_experiment_parser.add_argument("--status", "-s", choices=[s.value for s in ExperimentStatus], default=ExperimentStatus.PLANNED.value, help="Experiment status")
    create_experiment_parser.add_argument("--question", "-q", help="Related research question ID")
    
    # Create from template
    template_experiment_parser = experiment_subparsers.add_parser("template", help="Create an experiment from a template")
    template_experiment_parser.add_argument("--template", "-t", required=True, help="Template name")
    template_experiment_parser.add_argument("--values", "-v", nargs="+", help="Template values in key=value format")
    
    # List templates
    list_templates_parser = experiment_subparsers.add_parser("templates", help="List available experiment templates")
    
    # List experiments
    list_experiments_parser = experiment_subparsers.add_parser("list", help="List experiments")
    list_experiments_parser.add_argument("--status", choices=[s.value for s in ExperimentStatus], help="Filter by status")
    
    # View experiment
    view_experiment_parser = experiment_subparsers.add_parser("view", help="View an experiment")
    view_experiment_parser.add_argument("id", help="Experiment ID")
    
    # Grant proposal commands
    grant_parser = subparsers.add_parser("grant", help="Manage grant proposals")
    grant_subparsers = grant_parser.add_subparsers(dest="grant_command", help="Grant proposal command")
    
    # Create grant
    create_grant_parser = grant_subparsers.add_parser("create", help="Create a new grant proposal")
    create_grant_parser.add_argument("--title", "-t", required=True, help="Proposal title")
    create_grant_parser.add_argument("--agency", "-a", required=True, help="Funding agency")
    create_grant_parser.add_argument("--description", "-d", required=True, help="Proposal description")
    create_grant_parser.add_argument("--deadline", help="Submission deadline (YYYY-MM-DD)")
    create_grant_parser.add_argument("--amount", type=float, help="Requested amount")
    create_grant_parser.add_argument("--status", "-s", choices=[s.value for s in GrantStatus], default=GrantStatus.DRAFTING.value, help="Proposal status")
    
    # List grants
    list_grants_parser = grant_subparsers.add_parser("list", help="List grant proposals")
    list_grants_parser.add_argument("--status", choices=[s.value for s in GrantStatus], help="Filter by status")
    
    # View grant
    view_grant_parser = grant_subparsers.add_parser("view", help="View a grant proposal")
    view_grant_parser.add_argument("id", help="Grant proposal ID")
    
    # Add to grant workspace
    add_to_grant_parser = grant_subparsers.add_parser("add", help="Add items to a grant proposal workspace")
    add_to_grant_parser.add_argument("id", help="Grant proposal ID")
    add_to_grant_parser.add_argument("--notes", nargs="+", help="Note IDs to add")
    add_to_grant_parser.add_argument("--experiments", nargs="+", help="Experiment IDs to add")
    add_to_grant_parser.add_argument("--questions", nargs="+", help="Research question IDs to add")
    
    # Export grant
    export_grant_parser = grant_subparsers.add_parser("export", help="Export a grant proposal")
    export_grant_parser.add_argument("id", help="Grant proposal ID")
    export_grant_parser.add_argument("--output", "-o", required=True, help="Output file path")
    
    # Collaborator commands
    collab_parser = subparsers.add_parser("collaborator", help="Manage collaborators")
    collab_subparsers = collab_parser.add_subparsers(dest="collab_command", help="Collaborator command")
    
    # Create collaborator
    create_collab_parser = collab_subparsers.add_parser("create", help="Create a new collaborator")
    create_collab_parser.add_argument("--name", "-n", required=True, help="Collaborator name")
    create_collab_parser.add_argument("--email", "-e", help="Email address")
    create_collab_parser.add_argument("--affiliation", "-a", help="Institutional affiliation")
    create_collab_parser.add_argument("--role", "-r", choices=[r.value for r in CollaboratorRole], default=CollaboratorRole.COLLABORATOR.value, help="Collaborator role")
    
    # Import annotations
    import_annotations_parser = collab_subparsers.add_parser("import", help="Import annotations from a collaborator")
    import_annotations_parser.add_argument("id", help="Collaborator ID")
    import_annotations_parser.add_argument("--file", "-f", required=True, help="Annotations file path")
    
    # Search commands
    search_parser = subparsers.add_parser("search", help="Search the knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--types", "-t", nargs="+", choices=["notes", "citations", "questions", "experiments", "grants"], help="Types of nodes to search")
    
    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup and restore")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", help="Backup command")
    
    # Create backup
    create_backup_parser = backup_subparsers.add_parser("create", help="Create a backup")
    create_backup_parser.add_argument("--dir", "-d", required=True, help="Backup directory")
    
    # Restore backup
    restore_backup_parser = backup_subparsers.add_parser("restore", help="Restore from a backup")
    restore_backup_parser.add_argument("--path", "-p", required=True, help="Backup path")
    
    args = parser.parse_args()
    
    # Handle case when no command is provided
    if not args.command:
        parser.print_help()
        return
    
    # Initialize the ResearchBrain system
    if args.command == "init":
        _init_command(args.data_dir)
        return
    
    # For all other commands, we need to have an initialized system
    rb = ResearchBrain(args.data_dir)
    
    # Dispatch to appropriate command handler
    if args.command == "note":
        _handle_note_command(rb, args)
    elif args.command == "citation":
        _handle_citation_command(rb, args)
    elif args.command == "question":
        _handle_question_command(rb, args)
    elif args.command == "experiment":
        _handle_experiment_command(rb, args)
    elif args.command == "grant":
        _handle_grant_command(rb, args)
    elif args.command == "collaborator":
        _handle_collaborator_command(rb, args)
    elif args.command == "search":
        _handle_search_command(rb, args)
    elif args.command == "backup":
        _handle_backup_command(rb, args)


def _init_command(data_dir: str) -> None:
    """Initialize a new knowledge base.
    
    Args:
        data_dir: Path to the data directory.
    """
    data_path = Path(data_dir)
    
    if data_path.exists() and any(data_path.iterdir()):
        console.print("[bold red]Error:[/bold red] Data directory already exists and is not empty.")
        console.print(f"Path: {data_path.absolute()}")
        return
    
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize the system to create necessary directories
    rb = ResearchBrain(data_path)
    
    console.print(Panel.fit(
        "[bold green]ResearchBrain initialized successfully![/bold green]\n\n"
        f"Data directory: {data_path.absolute()}\n\n"
        "You can now start adding notes, citations, and other knowledge items.",
        title="Initialization Complete"
    ))


def _handle_note_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle note-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.note_command:
        console.print("[bold red]Error:[/bold red] No note command specified.")
        return
    
    if args.note_command == "create":
        tags = set(args.tags) if args.tags else set()
        
        source_id = None
        if args.source:
            try:
                source_id = args.source
            except ValueError:
                console.print("[bold red]Error:[/bold red] Invalid source ID format.")
                return
        
        note_id = rb.create_note(
            title=args.title,
            content=args.content,
            tags=tags,
            source_id=source_id,
            page_reference=args.page
        )
        
        console.print(f"[bold green]Note created with ID:[/bold green] {note_id}")
    
    elif args.note_command == "list":
        notes = rb.storage.list_all(rb.core.models.Note)
        
        if args.tag:
            notes = [note for note in notes if args.tag in note.tags]
        
        # Sort by last modified
        notes.sort(key=lambda x: x.updated_at, reverse=True)
        
        # Apply limit
        notes = notes[:args.limit]
        
        if not notes:
            console.print("[italic]No notes found.[/italic]")
            return
        
        table = Table(title="Research Notes")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Tags")
        table.add_column("Last Modified", style="italic")
        
        for note in notes:
            tags_str = ", ".join(note.tags) if note.tags else ""
            table.add_row(
                str(note.id),
                note.title,
                tags_str,
                note.updated_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
    
    elif args.note_command == "view":
        try:
            note_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid note ID format.")
            return
        
        note = rb.get_note(note_id)
        if not note:
            console.print("[bold red]Error:[/bold red] Note not found.")
            return
        
        console.print(Panel(
            f"[bold]{note.title}[/bold]\n\n"
            f"{note.content}\n\n"
            f"[dim]Tags: {', '.join(note.tags) if note.tags else 'None'}[/dim]\n"
            f"[dim]Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]\n"
            f"[dim]Last Modified: {note.updated_at.strftime('%Y-%m-%d %H:%M')}[/dim]",
            title=f"Note ID: {note.id}"
        ))
    
    elif args.note_command == "update":
        try:
            note_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid note ID format.")
            return
        
        tags = set(args.tags) if args.tags else None
        
        success = rb.update_note(
            note_id=note_id,
            title=args.title,
            content=args.content,
            tags=tags
        )
        
        if success:
            console.print("[bold green]Note updated successfully.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to update note. Note not found.")
    
    elif args.note_command == "delete":
        try:
            note_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid note ID format.")
            return
        
        success = rb.delete_note(note_id)
        
        if success:
            console.print("[bold green]Note deleted successfully.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to delete note. Note not found.")


def _handle_citation_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle citation-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.citation_command:
        console.print("[bold red]Error:[/bold red] No citation command specified.")
        return
    
    if args.citation_command == "import":
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
            return
        
        citation_id = rb.import_paper(file_path)
        
        if citation_id:
            console.print(f"[bold green]Citation imported with ID:[/bold green] {citation_id}")
        else:
            console.print("[bold red]Error:[/bold red] Failed to import citation. Invalid or unsupported file.")
    
    elif args.citation_command == "create":
        citation_id = rb.create_citation(
            title=args.title,
            authors=args.authors,
            year=args.year,
            doi=args.doi,
            journal=args.journal
        )
        
        console.print(f"[bold green]Citation created with ID:[/bold green] {citation_id}")
    
    elif args.citation_command == "list":
        citations = rb.storage.list_all(rb.core.models.Citation)
        
        if args.author:
            citations = [c for c in citations if any(args.author.lower() in author.lower() for author in c.authors)]
        
        if args.year:
            citations = [c for c in citations if c.year == args.year]
        
        # Sort by year (most recent first)
        citations.sort(key=lambda x: (x.year if x.year else 0), reverse=True)
        
        # Apply limit
        citations = citations[:args.limit]
        
        if not citations:
            console.print("[italic]No citations found.[/italic]")
            return
        
        table = Table(title="Citations")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Authors")
        table.add_column("Year")
        table.add_column("Journal/Publisher")
        
        for citation in citations:
            authors_str = ", ".join(citation.authors) if len(citation.authors) <= 3 else f"{citation.authors[0]} et al."
            year_str = str(citation.year) if citation.year else ""
            journal_str = citation.journal if citation.journal else (citation.publisher if citation.publisher else "")
            
            table.add_row(
                str(citation.id),
                citation.title,
                authors_str,
                year_str,
                journal_str
            )
        
        console.print(table)
    
    elif args.citation_command == "view":
        try:
            citation_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid citation ID format.")
            return
        
        citation = rb.storage.get(rb.core.models.Citation, citation_id)
        if not citation:
            console.print("[bold red]Error:[/bold red] Citation not found.")
            return
        
        # Format the citation
        format_name = args.format
        formatted_citation = rb.generate_citation(citation_id, format_name)
        
        # Get linked notes
        linked_notes = []
        for note_id in citation.notes:
            note = rb.storage.get(rb.core.models.Note, note_id)
            if note:
                linked_notes.append(note)
        
        console.print(Panel(
            f"[bold]{citation.title}[/bold]\n\n"
            f"[bold]Authors:[/bold] {', '.join(citation.authors)}\n"
            f"[bold]Year:[/bold] {citation.year if citation.year else 'N/A'}\n"
            f"[bold]Journal/Publication:[/bold] {citation.journal if citation.journal else 'N/A'}\n"
            f"[bold]DOI:[/bold] {citation.doi if citation.doi else 'N/A'}\n\n"
            f"[bold]Formatted Citation ({format_name}):[/bold]\n"
            f"{formatted_citation}\n\n"
            f"[bold]Linked Notes:[/bold] {len(linked_notes)}\n" +
            "\n".join(f"- {note.title} ({note.id})" for note in linked_notes[:5]) +
            (f"\n  [italic]...and {len(linked_notes) - 5} more[/italic]" if len(linked_notes) > 5 else ""),
            title=f"Citation ID: {citation.id}"
        ))
    
    elif args.citation_command == "link":
        try:
            note_id = args.note_id
            citation_id = args.citation_id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid ID format.")
            return
        
        success = rb.link_note_to_paper(note_id, citation_id, args.page)
        
        if success:
            console.print("[bold green]Note linked to citation successfully.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to link note to citation. Note or citation not found.")


def _handle_question_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle research question-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.question_command:
        console.print("[bold red]Error:[/bold red] No research question command specified.")
        return
    
    if args.question_command == "create":
        tags = set(args.tags) if args.tags else set()
        
        question_id = rb.create_research_question(
            question=args.question,
            description=args.description,
            tags=tags,
            priority=args.priority
        )
        
        console.print(f"[bold green]Research question created with ID:[/bold green] {question_id}")
    
    elif args.question_command == "list":
        questions = rb.storage.list_all(rb.core.models.ResearchQuestion)
        
        if args.status:
            questions = [q for q in questions if q.status == args.status]
        
        if args.priority is not None:
            questions = [q for q in questions if q.priority >= args.priority]
        
        # Sort by priority (highest first)
        questions.sort(key=lambda x: x.priority, reverse=True)
        
        if not questions:
            console.print("[italic]No research questions found.[/italic]")
            return
        
        table = Table(title="Research Questions")
        table.add_column("ID", style="dim")
        table.add_column("Question", style="bold")
        table.add_column("Status")
        table.add_column("Priority")
        table.add_column("Evidence", justify="right")
        
        for question in questions:
            table.add_row(
                str(question.id),
                question.question,
                question.status,
                str(question.priority),
                str(len(question.evidence))
            )
        
        console.print(table)
    
    elif args.question_command == "view":
        try:
            question_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid question ID format.")
            return
        
        question = rb.storage.get(rb.core.models.ResearchQuestion, question_id)
        if not question:
            console.print("[bold red]Error:[/bold red] Research question not found.")
            return
        
        # Get evidence details
        evidence_items = []
        for evidence in question.evidence:
            note = rb.storage.get(rb.core.models.Note, evidence.note_id)
            note_title = note.title if note else "Unknown Note"
            evidence_items.append({
                "note_title": note_title,
                "note_id": evidence.note_id,
                "type": evidence.evidence_type,
                "strength": evidence.strength,
                "description": evidence.description
            })
        
        # Count evidence by type
        supporting = sum(1 for e in question.evidence if e.evidence_type == rb.core.models.EvidenceType.SUPPORTING)
        contradicting = sum(1 for e in question.evidence if e.evidence_type == rb.core.models.EvidenceType.CONTRADICTING)
        
        console.print(Panel(
            f"[bold]{question.question}[/bold]\n\n" +
            (f"{question.description}\n\n" if question.description else "") +
            f"[bold]Status:[/bold] {question.status} | [bold]Priority:[/bold] {question.priority}/10\n"
            f"[bold]Tags:[/bold] {', '.join(question.tags) if question.tags else 'None'}\n\n"
            f"[bold]Evidence Summary:[/bold]\n"
            f"- Supporting evidence: {supporting}\n"
            f"- Contradicting evidence: {contradicting}\n"
            f"- Total evidence items: {len(question.evidence)}\n\n"
            "[bold]Evidence Details:[/bold]",
            title=f"Research Question ID: {question.id}"
        ))
        
        if evidence_items:
            evidence_table = Table()
            evidence_table.add_column("Note")
            evidence_table.add_column("Type")
            evidence_table.add_column("Strength")
            evidence_table.add_column("Description")
            
            for item in evidence_items:
                evidence_table.add_row(
                    f"{item['note_title']} ({item['note_id']})",
                    item["type"].value,
                    item["strength"].value,
                    item["description"] if item["description"] else "No description"
                )
            
            console.print(evidence_table)
        else:
            console.print("[italic]No evidence has been added to this question yet.[/italic]")
    
    elif args.question_command == "evidence":
        try:
            question_id = args.question_id
            note_id = args.note_id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid ID format.")
            return
        
        evidence_id = rb.add_evidence_to_question(
            question_id=question_id,
            note_id=note_id,
            evidence_type=args.type,
            strength=args.strength,
            description=args.description
        )
        
        if evidence_id:
            console.print("[bold green]Evidence added successfully.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to add evidence. Question or note not found.")


def _handle_experiment_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle experiment-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.experiment_command:
        console.print("[bold red]Error:[/bold red] No experiment command specified.")
        return
    
    if args.experiment_command == "create":
        research_question_id = None
        if args.question:
            try:
                research_question_id = args.question
            except ValueError:
                console.print("[bold red]Error:[/bold red] Invalid research question ID format.")
                return
        
        experiment_id = rb.create_experiment(
            title=args.title,
            hypothesis=args.hypothesis,
            methodology=args.methodology,
            status=args.status,
            research_question_id=research_question_id
        )
        
        console.print(f"[bold green]Experiment created with ID:[/bold green] {experiment_id}")
    
    elif args.experiment_command == "template":
        # Parse template values
        template_values = {}
        if args.values:
            for value_str in args.values:
                if "=" in value_str:
                    key, value = value_str.split("=", 1)
                    template_values[key.strip()] = value.strip()
        
        experiment_id = rb.create_experiment_from_template(args.template, **template_values)
        
        if experiment_id:
            console.print(f"[bold green]Experiment created from template with ID:[/bold green] {experiment_id}")
        else:
            console.print("[bold red]Error:[/bold red] Failed to create experiment from template.")
    
    elif args.experiment_command == "templates":
        templates = list_templates()
        
        if not templates:
            console.print("[italic]No experiment templates found.[/italic]")
            return
        
        table = Table(title="Experiment Templates")
        table.add_column("Template Name", style="bold")
        
        for template_name in templates:
            table.add_row(template_name)
        
        console.print(table)
    
    elif args.experiment_command == "list":
        experiments = rb.storage.list_all(rb.core.models.Experiment)
        
        if args.status:
            experiments = [e for e in experiments if e.status.value == args.status]
        
        # Sort by status (in progress first, then planned, then others)
        def status_sort_key(experiment):
            if experiment.status == rb.core.models.ExperimentStatus.IN_PROGRESS:
                return 0
            elif experiment.status == rb.core.models.ExperimentStatus.PLANNED:
                return 1
            elif experiment.status == rb.core.models.ExperimentStatus.COMPLETED:
                return 2
            else:
                return 3
        
        experiments.sort(key=status_sort_key)
        
        if not experiments:
            console.print("[italic]No experiments found.[/italic]")
            return
        
        table = Table(title="Experiments")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Status")
        table.add_column("Research Question")
        table.add_column("Start Date")
        
        for experiment in experiments:
            # Get related research question if present
            question_title = "None"
            if experiment.research_question_id:
                question = rb.storage.get(rb.core.models.ResearchQuestion, experiment.research_question_id)
                if question:
                    question_title = question.question
            
            start_date = experiment.start_date.strftime("%Y-%m-%d") if experiment.start_date else "Not started"
            
            table.add_row(
                str(experiment.id),
                experiment.title,
                experiment.status.value,
                question_title,
                start_date
            )
        
        console.print(table)
    
    elif args.experiment_command == "view":
        try:
            experiment_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid experiment ID format.")
            return
        
        experiment = rb.storage.get(rb.core.models.Experiment, experiment_id)
        if not experiment:
            console.print("[bold red]Error:[/bold red] Experiment not found.")
            return
        
        # Get related research question if present
        question_info = "None"
        if experiment.research_question_id:
            question = rb.storage.get(rb.core.models.ResearchQuestion, experiment.research_question_id)
            if question:
                question_info = f"{question.question} ({experiment.research_question_id})"
        
        # Get related notes
        notes = []
        for note_id in experiment.notes:
            note = rb.storage.get(rb.core.models.Note, note_id)
            if note:
                notes.append(note)
        
        console.print(Panel(
            f"[bold]{experiment.title}[/bold]\n\n"
            f"[bold]Hypothesis:[/bold] {experiment.hypothesis}\n\n"
            f"[bold]Status:[/bold] {experiment.status.value}\n"
            f"[bold]Dates:[/bold] {experiment.start_date or 'Not started'} to {experiment.end_date or 'Not completed'}\n"
            f"[bold]Research Question:[/bold] {question_info}\n\n"
            f"[bold]Methodology:[/bold]\n{experiment.methodology}\n\n" +
            (f"[bold]Results:[/bold]\n{experiment.results}\n\n" if experiment.results else "") +
            (f"[bold]Conclusion:[/bold]\n{experiment.conclusion}\n\n" if experiment.conclusion else "") +
            f"[bold]Related Notes:[/bold] {len(notes)}\n" +
            "\n".join(f"- {note.title} ({note.id})" for note in notes[:5]) +
            (f"\n  [italic]...and {len(notes) - 5} more[/italic]" if len(notes) > 5 else ""),
            title=f"Experiment ID: {experiment.id}"
        ))


def _handle_grant_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle grant proposal-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.grant_command:
        console.print("[bold red]Error:[/bold red] No grant proposal command specified.")
        return
    
    if args.grant_command == "create":
        deadline = None
        if args.deadline:
            try:
                deadline = datetime.strptime(args.deadline, "%Y-%m-%d")
            except ValueError:
                console.print("[bold red]Error:[/bold red] Invalid deadline format. Use YYYY-MM-DD.")
                return
        
        grant_id = rb.create_grant_proposal(
            title=args.title,
            funding_agency=args.agency,
            description=args.description,
            deadline=deadline,
            amount=args.amount,
            status=args.status
        )
        
        console.print(f"[bold green]Grant proposal created with ID:[/bold green] {grant_id}")
    
    elif args.grant_command == "list":
        grants = rb.storage.list_all(rb.core.models.GrantProposal)
        
        if args.status:
            grants = [g for g in grants if g.status.value == args.status]
        
        # Sort by deadline (closest first, then those without deadlines)
        def deadline_sort_key(grant):
            if grant.deadline:
                return (0, grant.deadline)
            else:
                return (1, datetime.max)
        
        grants.sort(key=deadline_sort_key)
        
        if not grants:
            console.print("[italic]No grant proposals found.[/italic]")
            return
        
        table = Table(title="Grant Proposals")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Funding Agency")
        table.add_column("Status")
        table.add_column("Deadline")
        table.add_column("Amount")
        
        for grant in grants:
            deadline_str = grant.deadline.strftime("%Y-%m-%d") if grant.deadline else "No deadline"
            amount_str = f"${grant.amount:,.2f}" if grant.amount else "Not specified"
            
            table.add_row(
                str(grant.id),
                grant.title,
                grant.funding_agency,
                grant.status.value,
                deadline_str,
                amount_str
            )
        
        console.print(table)
    
    elif args.grant_command == "view":
        try:
            grant_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid grant proposal ID format.")
            return
        
        grant = rb.storage.get(rb.core.models.GrantProposal, grant_id)
        if not grant:
            console.print("[bold red]Error:[/bold red] Grant proposal not found.")
            return
        
        # Get related items
        notes = []
        for note_id in grant.notes:
            note = rb.storage.get(rb.core.models.Note, note_id)
            if note:
                notes.append(note)
        
        experiments = []
        for exp_id in grant.experiments:
            experiment = rb.storage.get(rb.core.models.Experiment, exp_id)
            if experiment:
                experiments.append(experiment)
        
        questions = []
        for q_id in grant.research_questions:
            question = rb.storage.get(rb.core.models.ResearchQuestion, q_id)
            if question:
                questions.append(question)
        
        console.print(Panel(
            f"[bold]{grant.title}[/bold]\n\n"
            f"[bold]Funding Agency:[/bold] {grant.funding_agency}\n"
            f"[bold]Status:[/bold] {grant.status.value}\n"
            f"[bold]Deadline:[/bold] {grant.deadline.strftime('%Y-%m-%d') if grant.deadline else 'No deadline'}\n"
            f"[bold]Amount:[/bold] {f'${grant.amount:,.2f}' if grant.amount else 'Not specified'}\n\n"
            f"[bold]Description:[/bold]\n{grant.description}\n\n"
            f"[bold]Research Questions:[/bold] {len(questions)}\n" +
            "\n".join(f"- {q.question} ({q.id})" for q in questions[:3]) +
            (f"\n  [italic]...and {len(questions) - 3} more[/italic]" if len(questions) > 3 else "") +
            f"\n\n[bold]Experiments:[/bold] {len(experiments)}\n" +
            "\n".join(f"- {e.title} ({e.id})" for e in experiments[:3]) +
            (f"\n  [italic]...and {len(experiments) - 3} more[/italic]" if len(experiments) > 3 else "") +
            f"\n\n[bold]Notes:[/bold] {len(notes)}\n" +
            "\n".join(f"- {n.title} ({n.id})" for n in notes[:3]) +
            (f"\n  [italic]...and {len(notes) - 3} more[/italic]" if len(notes) > 3 else ""),
            title=f"Grant Proposal ID: {grant.id}"
        ))
    
    elif args.grant_command == "add":
        try:
            grant_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid grant proposal ID format.")
            return
        
        note_ids = []
        if args.notes:
            for note_id_str in args.notes:
                try:
                    note_ids.append(note_id_str)
                except ValueError:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Invalid note ID format: {note_id_str}")
        
        experiment_ids = []
        if args.experiments:
            for exp_id_str in args.experiments:
                try:
                    experiment_ids.append(exp_id_str)
                except ValueError:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Invalid experiment ID format: {exp_id_str}")
        
        question_ids = []
        if args.questions:
            for q_id_str in args.questions:
                try:
                    question_ids.append(q_id_str)
                except ValueError:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Invalid question ID format: {q_id_str}")
        
        success = rb.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=note_ids if note_ids else None,
            experiment_ids=experiment_ids if experiment_ids else None,
            question_ids=question_ids if question_ids else None
        )
        
        if success:
            items_added = len(note_ids) + len(experiment_ids) + len(question_ids)
            console.print(f"[bold green]{items_added} items added to grant proposal workspace.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to add items to grant proposal. Grant not found.")
    
    elif args.grant_command == "export":
        try:
            grant_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid grant proposal ID format.")
            return
        
        output_path = Path(args.output)
        
        # Get the grant and related items
        grant = rb.storage.get(rb.core.models.GrantProposal, grant_id)
        if not grant:
            console.print("[bold red]Error:[/bold red] Grant proposal not found.")
            return
        
        notes = []
        for note_id in grant.notes:
            note = rb.storage.get(rb.core.models.Note, note_id)
            if note:
                notes.append(note)
        
        experiments = []
        for exp_id in grant.experiments:
            experiment = rb.storage.get(rb.core.models.Experiment, exp_id)
            if experiment:
                experiments.append(experiment)
        
        questions = []
        for q_id in grant.research_questions:
            question = rb.storage.get(rb.core.models.ResearchQuestion, q_id)
            if question:
                questions.append(question)
        
        from researchbrain.grants.export import export_proposal
        success = export_proposal(grant, notes, experiments, questions, output_path)
        
        if success:
            console.print(f"[bold green]Grant proposal exported successfully to:[/bold green] {output_path}")
        else:
            console.print("[bold red]Error:[/bold red] Failed to export grant proposal.")


def _handle_collaborator_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle collaborator-related commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.collab_command:
        console.print("[bold red]Error:[/bold red] No collaborator command specified.")
        return
    
    if args.collab_command == "create":
        collaborator_id = rb.create_collaborator(
            name=args.name,
            email=args.email,
            affiliation=args.affiliation,
            role=args.role
        )
        
        console.print(f"[bold green]Collaborator created with ID:[/bold green] {collaborator_id}")
    
    elif args.collab_command == "import":
        try:
            collaborator_id = args.id
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid collaborator ID format.")
            return
        
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
            return
        
        imported_count = rb.import_collaborator_annotations(collaborator_id, file_path)
        
        if imported_count > 0:
            console.print(f"[bold green]Successfully imported {imported_count} annotations.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to import annotations. Check file format or collaborator ID.")


def _handle_search_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle search command.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    node_types = args.types if args.types else None
    
    results = rb.search(args.query, node_types)
    
    if not any(results.values()):
        console.print(f"[italic]No results found for query: {args.query}[/italic]")
        return
    
    console.print(Panel(f"[bold]Search Results for:[/bold] {args.query}", title="Search Results"))
    
    # Notes
    if "notes" in results and results["notes"]:
        console.print("\n[bold]Notes:[/bold]")
        note_table = Table()
        note_table.add_column("ID", style="dim")
        note_table.add_column("Title", style="bold")
        note_table.add_column("Tags")
        note_table.add_column("Last Modified", style="italic")
        
        for note in results["notes"][:10]:  # Limit to 10 results
            tags_str = ", ".join(note.tags) if note.tags else ""
            note_table.add_row(
                str(note.id),
                note.title,
                tags_str,
                note.updated_at.strftime("%Y-%m-%d")
            )
        
        console.print(note_table)
        if len(results["notes"]) > 10:
            console.print(f"[italic]...and {len(results['notes']) - 10} more notes[/italic]")
    
    # Citations
    if "citations" in results and results["citations"]:
        console.print("\n[bold]Citations:[/bold]")
        citation_table = Table()
        citation_table.add_column("ID", style="dim")
        citation_table.add_column("Title", style="bold")
        citation_table.add_column("Authors")
        citation_table.add_column("Year")
        
        for citation in results["citations"][:10]:  # Limit to 10 results
            authors_str = ", ".join(citation.authors) if len(citation.authors) <= 3 else f"{citation.authors[0]} et al."
            year_str = str(citation.year) if citation.year else ""
            
            citation_table.add_row(
                str(citation.id),
                citation.title,
                authors_str,
                year_str
            )
        
        console.print(citation_table)
        if len(results["citations"]) > 10:
            console.print(f"[italic]...and {len(results['citations']) - 10} more citations[/italic]")
    
    # Research Questions
    if "questions" in results and results["questions"]:
        console.print("\n[bold]Research Questions:[/bold]")
        question_table = Table()
        question_table.add_column("ID", style="dim")
        question_table.add_column("Question", style="bold")
        question_table.add_column("Status")
        question_table.add_column("Priority")
        
        for question in results["questions"][:10]:  # Limit to 10 results
            question_table.add_row(
                str(question.id),
                question.question,
                question.status,
                str(question.priority)
            )
        
        console.print(question_table)
        if len(results["questions"]) > 10:
            console.print(f"[italic]...and {len(results['questions']) - 10} more questions[/italic]")
    
    # Experiments
    if "experiments" in results and results["experiments"]:
        console.print("\n[bold]Experiments:[/bold]")
        experiment_table = Table()
        experiment_table.add_column("ID", style="dim")
        experiment_table.add_column("Title", style="bold")
        experiment_table.add_column("Status")
        
        for experiment in results["experiments"][:10]:  # Limit to 10 results
            experiment_table.add_row(
                str(experiment.id),
                experiment.title,
                experiment.status.value
            )
        
        console.print(experiment_table)
        if len(results["experiments"]) > 10:
            console.print(f"[italic]...and {len(results['experiments']) - 10} more experiments[/italic]")
    
    # Grant Proposals
    if "grants" in results and results["grants"]:
        console.print("\n[bold]Grant Proposals:[/bold]")
        grant_table = Table()
        grant_table.add_column("ID", style="dim")
        grant_table.add_column("Title", style="bold")
        grant_table.add_column("Funding Agency")
        grant_table.add_column("Status")
        
        for grant in results["grants"][:10]:  # Limit to 10 results
            grant_table.add_row(
                str(grant.id),
                grant.title,
                grant.funding_agency,
                grant.status.value
            )
        
        console.print(grant_table)
        if len(results["grants"]) > 10:
            console.print(f"[italic]...and {len(results['grants']) - 10} more grant proposals[/italic]")


def _handle_backup_command(rb: ResearchBrain, args: argparse.Namespace) -> None:
    """Handle backup and restore commands.
    
    Args:
        rb: ResearchBrain instance.
        args: Command-line arguments.
    """
    if not args.backup_command:
        console.print("[bold red]Error:[/bold red] No backup command specified.")
        return
    
    if args.backup_command == "create":
        backup_dir = Path(args.dir)
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True)
        
        backup_path = rb.backup_knowledge_base(backup_dir)
        
        if backup_path:
            console.print(f"[bold green]Backup created successfully at:[/bold green] {backup_path}")
        else:
            console.print("[bold red]Error:[/bold red] Failed to create backup.")
    
    elif args.backup_command == "restore":
        backup_path = Path(args.path)
        if not backup_path.exists():
            console.print(f"[bold red]Error:[/bold red] Backup path not found: {backup_path}")
            return
        
        success = rb.restore_from_backup(backup_path)
        
        if success:
            console.print("[bold green]Knowledge base restored successfully from backup.[/bold green]")
        else:
            console.print("[bold red]Error:[/bold red] Failed to restore from backup.")


if __name__ == "__main__":
    main()