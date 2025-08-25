"""
Task management module for tracking research tasks and questions.

This module provides functionality for creating, updating, and managing
research tasks, organizing them into hierarchies, associating them with
research questions, and linking them with other research artifacts.
"""

from .models import ResearchTask, ResearchQuestion, TaskStatus, TaskPriority
from .storage import TaskStorageInterface, InMemoryTaskStorage
from .service import TaskManagementService, TaskService