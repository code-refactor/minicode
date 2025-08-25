"""
Learning mode manager for the text editor.
"""
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field
import time
import os
import inspect

from text_editor.learning.models import (
    Concept, 
    ConceptCategory, 
    ConceptDifficulty, 
    Annotation,
    ExtensionProject,
    LearningProgress
)

# Define default concepts
DEFAULT_CONCEPTS = [
    # Basic Concepts
    Concept(
        id="text_buffer",
        name="Text Buffer",
        description="Core data structure for storing and manipulating text.",
        category=ConceptCategory.DATA_STRUCTURES,
        difficulty=ConceptDifficulty.BASIC,
        examples=["A text buffer stores lines of text and provides operations for manipulation."],
        module_path="text_editor.core.buffer"
    ),
    Concept(
        id="cursor",
        name="Cursor",
        description="Tracks the current editing position within the text buffer.",
        category=ConceptCategory.EDITOR_INTERNALS,
        difficulty=ConceptDifficulty.BASIC,
        prerequisites=["text_buffer"],
        examples=["A cursor maintains a line and column position."],
        module_path="text_editor.core.cursor"
    ),
    Concept(
        id="basic_editing",
        name="Basic Editing Operations",
        description="Fundamental operations for inserting and deleting text.",
        category=ConceptCategory.EDITOR_INTERNALS,
        difficulty=ConceptDifficulty.BASIC,
        prerequisites=["text_buffer", "cursor"],
        examples=["Insert and delete operations modify the buffer at the cursor position."],
        module_path="text_editor.core.editor"
    ),
    
    # Intermediate Concepts
    Concept(
        id="undo_redo",
        name="Undo/Redo System",
        description="History management for reversible editing operations.",
        category=ConceptCategory.DESIGN_PATTERNS,
        difficulty=ConceptDifficulty.INTERMEDIATE,
        prerequisites=["basic_editing"],
        related_concepts=["command_pattern"],
        examples=["The undo/redo system uses a stack to track operations."],
        module_path="text_editor.core.history"
    ),
    Concept(
        id="file_operations",
        name="File Operations",
        description="Loading and saving text from files.",
        category=ConceptCategory.EDITOR_INTERNALS,
        difficulty=ConceptDifficulty.INTERMEDIATE,
        prerequisites=["text_buffer"],
        examples=["File operations handle encoding and error cases."],
        module_path="text_editor.core.file_manager"
    ),
    Concept(
        id="progressive_features",
        name="Progressive Feature System",
        description="System for gradually revealing features based on user skill.",
        category=ConceptCategory.USER_INTERFACE,
        difficulty=ConceptDifficulty.INTERMEDIATE,
        examples=["Features are organized by skill level and prerequisites."],
        module_path="text_editor.features.manager"
    ),
    
    # Advanced Concepts
    Concept(
        id="command_pattern",
        name="Command Pattern",
        description="Design pattern for encapsulating operations as objects.",
        category=ConceptCategory.DESIGN_PATTERNS,
        difficulty=ConceptDifficulty.ADVANCED,
        prerequisites=["undo_redo"],
        examples=["Each editing operation is represented as a command object."],
        module_path="text_editor.core.history"
    ),
    Concept(
        id="text_search",
        name="Text Search Algorithms",
        description="Algorithms for finding text within a document.",
        category=ConceptCategory.ALGORITHMS,
        difficulty=ConceptDifficulty.ADVANCED,
        prerequisites=["text_buffer"],
        examples=["Implementing efficient text search requires algorithms like Boyer-Moore."],
        module_path="text_editor.features.integration"
    ),
    Concept(
        id="editor_architecture",
        name="Text Editor Architecture",
        description="Overall architecture of a text editor.",
        category=ConceptCategory.SOFTWARE_ARCHITECTURE,
        difficulty=ConceptDifficulty.ADVANCED,
        prerequisites=["text_buffer", "cursor", "basic_editing", "file_operations"],
        examples=["A text editor typically has a model-view-controller architecture."],
        module_path="text_editor.core.editor"
    ),
    
    # Expert Concepts
    Concept(
        id="text_rendering",
        name="Text Rendering",
        description="Converting buffer contents to visual display.",
        category=ConceptCategory.EDITOR_INTERNALS,
        difficulty=ConceptDifficulty.EXPERT,
        prerequisites=["text_buffer"],
        examples=["Text rendering involves layout, line wrapping, and style application."],
        module_path=None  # Not implemented in our editor
    ),
    Concept(
        id="syntax_highlighting",
        name="Syntax Highlighting",
        description="Coloring text based on language syntax.",
        category=ConceptCategory.EDITOR_INTERNALS,
        difficulty=ConceptDifficulty.EXPERT,
        prerequisites=["text_buffer", "text_rendering"],
        examples=["Syntax highlighting uses language parsers to identify syntax elements."],
        module_path=None  # Not implemented in our editor
    ),
    Concept(
        id="gap_buffer",
        name="Gap Buffer",
        description="Efficient data structure for text editing.",
        category=ConceptCategory.DATA_STRUCTURES,
        difficulty=ConceptDifficulty.EXPERT,
        prerequisites=["text_buffer"],
        examples=["A gap buffer maintains a gap at the cursor position for efficient insertion."],
        module_path=None  # Not implemented in our editor
    ),
]

# Define default extension projects
DEFAULT_EXTENSION_PROJECTS = [
    ExtensionProject(
        id="simple_find",
        name="Simple Text Search",
        description="Implement a basic text search function for the editor.",
        difficulty=ConceptDifficulty.BASIC,
        concepts=["text_buffer", "cursor"],
        requirements=[
            "Implement a function that searches for a string in the buffer",
            "Return the position (line, column) of the first match",
            "Return None if no match is found"
        ],
        starter_code="""
def find_text(buffer, search_string, start_line=0, start_col=0):
    # Your implementation here
    pass
""",
        solution_code="""
def find_text(buffer, search_string, start_line=0, start_col=0):
    for line_num in range(start_line, buffer.get_line_count()):
        line_text = buffer.get_line(line_num)
        
        # For the first line, start from the specified column
        col = start_col if line_num == start_line else 0
        
        # Search in this line
        found_pos = line_text.find(search_string, col)
        if found_pos >= 0:
            return {
                "line": line_num,
                "column": found_pos
            }
    
    return None
""",
        tests=[
            "assert find_text(buffer_with_text('hello world'), 'world', 0, 0) == {'line': 0, 'column': 6}",
            "assert find_text(buffer_with_text('hello\\nworld'), 'world', 0, 0) == {'line': 1, 'column': 0}",
            "assert find_text(buffer_with_text('hello world'), 'not found', 0, 0) is None"
        ],
        hints=[
            "Use buffer.get_line_count() to get the number of lines",
            "Use buffer.get_line(line_num) to get a specific line",
            "Use the string.find() method to search within a line"
        ],
        estimated_time_minutes=30
    ),
    ExtensionProject(
        id="line_word_counter",
        name="Line and Word Counter",
        description="Implement functions to count lines and words in the editor.",
        difficulty=ConceptDifficulty.BASIC,
        concepts=["text_buffer"],
        requirements=[
            "Implement a function that counts the number of lines",
            "Implement a function that counts the number of words",
            "Handle empty buffers and edge cases"
        ],
        starter_code="""
def count_lines(buffer):
    # Your implementation here
    pass

def count_words(buffer):
    # Your implementation here
    pass
""",
        solution_code="""
def count_lines(buffer):
    return buffer.get_line_count()

def count_words(buffer):
    word_count = 0
    for line_num in range(buffer.get_line_count()):
        line_text = buffer.get_line(line_num)
        word_count += len(line_text.split())
    return word_count
""",
        tests=[
            "assert count_lines(buffer_with_text('hello world')) == 1",
            "assert count_lines(buffer_with_text('hello\\nworld')) == 2",
            "assert count_lines(buffer_with_text('')) == 1",  # Empty buffer has one empty line
            "assert count_words(buffer_with_text('hello world')) == 2",
            "assert count_words(buffer_with_text('hello\\nworld')) == 2",
            "assert count_words(buffer_with_text('')) == 0"
        ],
        hints=[
            "Use buffer.get_line_count() to get the number of lines",
            "Use string.split() to split a line into words",
            "Remember that an empty buffer still has one empty line"
        ],
        estimated_time_minutes=20
    ),
    ExtensionProject(
        id="selection_mechanism",
        name="Text Selection Mechanism",
        description="Implement a mechanism for selecting and manipulating text ranges.",
        difficulty=ConceptDifficulty.INTERMEDIATE,
        concepts=["text_buffer", "cursor", "basic_editing"],
        requirements=[
            "Define a Selection class that tracks the start and end positions",
            "Implement methods to expand/shrink the selection",
            "Implement methods to get the selected text",
            "Implement methods to delete or replace the selected text"
        ],
        starter_code="""
class Selection:
    def __init__(self, buffer, start_line, start_col, end_line, end_col):
        # Your implementation here
        pass
        
    def get_selected_text(self):
        # Your implementation here
        pass
        
    def delete_selected_text(self):
        # Your implementation here
        pass
        
    def replace_selected_text(self, new_text):
        # Your implementation here
        pass
""",
        solution_code="""
class Selection:
    def __init__(self, buffer, start_line, start_col, end_line, end_col):
        self.buffer = buffer
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        
    def get_selected_text(self):
        # Handle single line case
        if self.start_line == self.end_line:
            line = self.buffer.get_line(self.start_line)
            return line[self.start_col:self.end_col]
        
        # Handle multi-line case
        selected_text = []
        
        # First line
        selected_text.append(self.buffer.get_line(self.start_line)[self.start_col:])
        
        # Middle lines
        for line_num in range(self.start_line + 1, self.end_line):
            selected_text.append(self.buffer.get_line(line_num))
        
        # Last line
        selected_text.append(self.buffer.get_line(self.end_line)[:self.end_col])
        
        return '\\n'.join(selected_text)
        
    def delete_selected_text(self):
        deleted_text = self.get_selected_text()
        self.buffer.delete_text(self.start_line, self.start_col, 
                              self.end_line, self.end_col)
        return deleted_text
        
    def replace_selected_text(self, new_text):
        deleted_text = self.get_selected_text()
        self.buffer.replace_text(self.start_line, self.start_col,
                               self.end_line, self.end_col, new_text)
        return deleted_text
""",
        tests=[
            "selection = Selection(buffer_with_text('hello world'), 0, 0, 0, 5)",
            "assert selection.get_selected_text() == 'hello'",
            "selection = Selection(buffer_with_text('hello\\nworld'), 0, 0, 1, 5)",
            "assert selection.get_selected_text() == 'hello\\nworld'",
            "buffer = buffer_with_text('hello world')",
            "selection = Selection(buffer, 0, 0, 0, 5)",
            "assert selection.delete_selected_text() == 'hello'",
            "assert buffer.get_content() == ' world'",
            "buffer = buffer_with_text('hello world')",
            "selection = Selection(buffer, 0, 0, 0, 5)",
            "selection.replace_selected_text('hi')",
            "assert buffer.get_content() == 'hi world'"
        ],
        hints=[
            "Handle single-line and multi-line selections differently",
            "Use buffer.get_line() to get text from each line",
            "Use buffer.delete_text() and buffer.replace_text() for editing"
        ],
        estimated_time_minutes=60
    ),
    ExtensionProject(
        id="custom_undo_redo",
        name="Custom Undo/Redo System",
        description="Implement a custom undo/redo system using the Command pattern.",
        difficulty=ConceptDifficulty.ADVANCED,
        concepts=["undo_redo", "command_pattern", "basic_editing"],
        requirements=[
            "Define a Command interface with execute, undo, and redo methods",
            "Implement concrete commands for insert, delete, and replace",
            "Create a History class to manage the undo and redo stacks",
            "Integrate the commands with the editor operations"
        ],
        starter_code="""
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass
        
    @abstractmethod
    def undo(self):
        pass
        
    @abstractmethod
    def redo(self):
        pass

class InsertCommand(Command):
    # Your implementation here
    pass
    
class DeleteCommand(Command):
    # Your implementation here
    pass
    
class History:
    # Your implementation here
    pass
""",
        solution_code="""
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass
        
    @abstractmethod
    def undo(self):
        pass
        
    @abstractmethod
    def redo(self):
        pass

class InsertCommand(Command):
    def __init__(self, buffer, line, column, text):
        self.buffer = buffer
        self.line = line
        self.column = column
        self.text = text
        
    def execute(self):
        self.buffer.insert_text(self.line, self.column, self.text)
        
    def undo(self):
        # Calculate end position based on inserted text
        if '\\n' in self.text:
            lines = self.text.split('\\n')
            end_line = self.line + len(lines) - 1
            end_column = len(lines[-1])
            if self.line == end_line:
                end_column += self.column
        else:
            end_line = self.line
            end_column = self.column + len(self.text)
            
        self.buffer.delete_text(self.line, self.column, end_line, end_column)
        
    def redo(self):
        self.execute()
    
class DeleteCommand(Command):
    def __init__(self, buffer, start_line, start_column, end_line, end_column):
        self.buffer = buffer
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column
        self.deleted_text = None
        
    def execute(self):
        self.deleted_text = self.buffer.delete_text(
            self.start_line, self.start_column, 
            self.end_line, self.end_column
        )
        return self.deleted_text
        
    def undo(self):
        if self.deleted_text is not None:
            self.buffer.insert_text(self.start_line, self.start_column, self.deleted_text)
        
    def redo(self):
        self.execute()
    
class History:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        
    def execute_command(self, command):
        result = command.execute()
        self.undo_stack.append(command)
        self.redo_stack = []  # Clear redo stack
        return result
        
    def undo(self):
        if not self.undo_stack:
            return False
            
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        return True
        
    def redo(self):
        if not self.redo_stack:
            return False
            
        command = self.redo_stack.pop()
        command.redo()
        self.undo_stack.append(command)
        return True
        
    def can_undo(self):
        return len(self.undo_stack) > 0
        
    def can_redo(self):
        return len(self.redo_stack) > 0
""",
        tests=[
            "buffer = buffer_with_text('')",
            "history = History()",
            "cmd = InsertCommand(buffer, 0, 0, 'hello')",
            "history.execute_command(cmd)",
            "assert buffer.get_content() == 'hello'",
            "history.undo()",
            "assert buffer.get_content() == ''",
            "history.redo()",
            "assert buffer.get_content() == 'hello'",
            "cmd = DeleteCommand(buffer, 0, 0, 0, 5)",
            "history.execute_command(cmd)",
            "assert buffer.get_content() == ''",
            "history.undo()",
            "assert buffer.get_content() == 'hello'"
        ],
        hints=[
            "Use buffer.insert_text() and buffer.delete_text() in your commands",
            "Save enough state in each command to perform the undo operation",
            "Remember to calculate the correct end position after text insertion",
            "Clear the redo stack when a new command is executed"
        ],
        estimated_time_minutes=90
    ),
]


class LearningManager(BaseModel):
    """
    Manages the learning mode system for the text editor.
    
    This class provides access to annotated source code, manages extension
    projects, and tracks the user's progress in learning concepts.
    """
    concepts: Dict[str, Concept] = Field(default_factory=dict)
    annotation_cache: Dict[str, List[Annotation]] = Field(default_factory=dict)
    extension_projects: Dict[str, ExtensionProject] = Field(default_factory=dict)
    learning_progress: LearningProgress = Field(default_factory=LearningProgress)
    
    def __init__(self, **kwargs):
        """Initialize the learning manager with default concepts and projects."""
        super().__init__(**kwargs)
        
        # Initialize with default concepts
        for concept in DEFAULT_CONCEPTS:
            self.concepts[concept.id] = concept
        
        # Initialize with default extension projects
        for project in DEFAULT_EXTENSION_PROJECTS:
            self.extension_projects[project.id] = project
    
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """
        Get a specific concept by ID.
        
        Args:
            concept_id: ID of the concept to retrieve
            
        Returns:
            The Concept object, or None if not found
        """
        return self.concepts.get(concept_id)
    
    def get_all_concepts(self) -> List[Concept]:
        """
        Get all available concepts.
        
        Returns:
            List of all Concept objects
        """
        return list(self.concepts.values())
    
    def get_concepts_by_category(self, category: ConceptCategory) -> List[Concept]:
        """
        Get concepts filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of Concept objects in the specified category
        """
        return [c for c in self.concepts.values() if c.category == category]
    
    def get_concepts_by_difficulty(self, difficulty: ConceptDifficulty) -> List[Concept]:
        """
        Get concepts filtered by difficulty.
        
        Args:
            difficulty: Difficulty level to filter by
            
        Returns:
            List of Concept objects at the specified difficulty
        """
        return [c for c in self.concepts.values() if c.difficulty == difficulty]
    
    def get_annotated_source(self, concept_id: str) -> List[Annotation]:
        """
        Get annotated source code for a concept.
        
        This method dynamically analyzes the actual source code of the module
        implementing the concept and adds annotations explaining key parts.
        
        Args:
            concept_id: ID of the concept to get annotations for
            
        Returns:
            List of Annotation objects for the concept
        """
        start_time = time.time()
        
        # Check if annotations are already cached
        if concept_id in self.annotation_cache:
            return self.annotation_cache[concept_id]
            
        concept = self.get_concept(concept_id)
        if not concept or not concept.module_path:
            return []
            
        # Load the module dynamically
        try:
            module = __import__(concept.module_path, fromlist=[""])
            source_code = inspect.getsource(module)
            source_lines = source_code.split("\n")
        except (ImportError, ValueError):
            return []
            
        # Create annotations based on the concept
        annotations = []
        
        # For demo purposes, we create some simple annotations
        # In a real implementation, this would be more sophisticated
        
        # Find class definitions
        class_lines = []
        for i, line in enumerate(source_lines):
            if line.startswith("class "):
                class_lines.append(i)
        
        for class_line in class_lines:
            # Find the end of the class definition
            class_name = source_lines[class_line].split("class ")[1].split("(")[0].strip()
            class_end = len(source_lines)
            
            for i in range(class_line + 1, len(source_lines)):
                if i + 1 < len(source_lines) and source_lines[i + 1].startswith("class "):
                    class_end = i + 1
                    break
            
            # Create an annotation for the class
            class_snippet = "\n".join(source_lines[class_line:min(class_line + 10, class_end)])
            annotations.append(
                Annotation(
                    concept_id=concept_id,
                    start_line=class_line,
                    end_line=min(class_line + 10, class_end),
                    text=f"This is the {class_name} class which is central to the {concept.name} concept. "
                         f"It implements {concept.description}",
                    code_snippet=class_snippet
                )
            )
            
            # Find methods in the class
            method_lines = []
            for i in range(class_line, class_end):
                line = source_lines[i]
                if line.strip().startswith("def ") and i > 0 and "self" in line:
                    method_lines.append(i)
            
            # Create annotations for important methods
            for method_line in method_lines[:3]:  # Limit to 3 methods for demo
                method_name = source_lines[method_line].split("def ")[1].split("(")[0].strip()
                
                # Find the end of the method
                method_end = class_end
                for i in range(method_line + 1, class_end):
                    if source_lines[i].strip().startswith("def ") and "self" in source_lines[i]:
                        method_end = i
                        break
                
                # Create an annotation for the method
                method_snippet = "\n".join(source_lines[method_line:min(method_line + 8, method_end)])
                annotations.append(
                    Annotation(
                        concept_id=concept_id,
                        start_line=method_line,
                        end_line=min(method_line + 8, method_end),
                        text=f"The {method_name} method is a key operation in the {concept.name} concept.",
                        code_snippet=method_snippet
                    )
                )
        
        # Cache the annotations
        self.annotation_cache[concept_id] = annotations
        
        # Mark the concept as viewed
        self.learning_progress.mark_concept_viewed(concept_id)
        
        # Calculate loading time for performance metrics
        load_time_ms = (time.time() - start_time) * 1000
        
        return annotations
    
    def get_extension_project(self, project_id: str) -> Optional[ExtensionProject]:
        """
        Get a specific extension project by ID.
        
        Args:
            project_id: ID of the project to retrieve
            
        Returns:
            The ExtensionProject object, or None if not found
        """
        return self.extension_projects.get(project_id)
    
    def get_all_extension_projects(self) -> List[ExtensionProject]:
        """
        Get all available extension projects.
        
        Returns:
            List of all ExtensionProject objects
        """
        return list(self.extension_projects.values())
    
    def get_projects_by_difficulty(self, difficulty: ConceptDifficulty) -> List[ExtensionProject]:
        """
        Get extension projects filtered by difficulty.
        
        Args:
            difficulty: Difficulty level to filter by
            
        Returns:
            List of ExtensionProject objects at the specified difficulty
        """
        return [p for p in self.extension_projects.values() if p.difficulty == difficulty]
    
    def get_projects_by_concept(self, concept_id: str) -> List[ExtensionProject]:
        """
        Get extension projects related to a specific concept.
        
        Args:
            concept_id: ID of the concept to find projects for
            
        Returns:
            List of ExtensionProject objects related to the concept
        """
        return [p for p in self.extension_projects.values() if concept_id in p.concepts]
    
    def get_recommended_projects(self) -> List[ExtensionProject]:
        """
        Get extension projects recommended based on the user's progress.
        
        Returns:
            List of recommended ExtensionProject objects
        """
        # Get completed concepts
        completed_concepts = self.learning_progress.completed_concepts
        
        # Get projects that use concepts the user has completed
        matching_projects = []
        for project in self.extension_projects.values():
            # Skip completed projects
            if project.id in self.learning_progress.completed_projects:
                continue
                
            # Check if the user has completed all required concepts
            required_concepts = set(project.concepts)
            if required_concepts.issubset(completed_concepts):
                matching_projects.append(project)
                
        return matching_projects
    
    def start_extension_project(self, project_id: str) -> bool:
        """
        Start working on an extension project.
        
        Args:
            project_id: ID of the project to start
            
        Returns:
            True if the project was successfully started, False otherwise
        """
        if project_id not in self.extension_projects:
            return False
            
        self.learning_progress.set_current_project(project_id)
        return True
    
    def complete_extension_project(self, project_id: str) -> bool:
        """
        Mark an extension project as completed.
        
        Args:
            project_id: ID of the project to complete
            
        Returns:
            True if the project was successfully completed, False otherwise
        """
        if project_id not in self.extension_projects:
            return False
            
        # Mark the project as completed
        self.learning_progress.mark_project_completed(project_id)
        
        # Mark related concepts as completed
        project = self.extension_projects[project_id]
        for concept_id in project.concepts:
            self.learning_progress.mark_concept_completed(concept_id)
            
        return True
    
    def get_learning_progress(self) -> Dict[str, Any]:
        """
        Get a summary of the user's learning progress.
        
        Returns:
            Dictionary with progress information
        """
        total_concepts = len(self.concepts)
        completed_concepts = len(self.learning_progress.completed_concepts)
        total_projects = len(self.extension_projects)
        completed_projects = len(self.learning_progress.completed_projects)
        
        # Calculate overall mastery
        if total_concepts > 0:
            overall_mastery = completed_concepts / total_concepts
        else:
            overall_mastery = 0.0
            
        return {
            "completed_concepts": completed_concepts,
            "total_concepts": total_concepts,
            "completed_projects": completed_projects,
            "total_projects": total_projects,
            "overall_mastery": overall_mastery,
            "current_project": self.learning_progress.current_project
        }
    
    def get_concept_mastery(self, concept_id: str) -> float:
        """
        Get the mastery level for a specific concept.
        
        Args:
            concept_id: ID of the concept to check
            
        Returns:
            Mastery level from 0.0 to 1.0
        """
        return self.learning_progress.get_mastery_level(concept_id)