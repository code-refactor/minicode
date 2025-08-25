"""
Data models for the interview preparation system.
"""
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel, Field
import time


class DifficultyLevel(Enum):
    """Difficulty levels for interview problems."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProblemCategory(Enum):
    """Categories of interview problems."""
    ARRAYS = "arrays"
    STRINGS = "strings"
    LINKED_LISTS = "linked_lists"
    TREES = "trees"
    GRAPHS = "graphs"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    RECURSION = "recursion"
    SORTING = "sorting"
    SEARCHING = "searching"
    HASH_TABLES = "hash_tables"
    MATH = "math"
    BIT_MANIPULATION = "bit_manipulation"


class TestCase(BaseModel):
    """
    Represents a test case for an interview problem.
    """
    input: str
    expected_output: str
    explanation: Optional[str] = None
    is_hidden: bool = False


class InterviewProblem(BaseModel):
    """
    Represents an interview practice problem.
    """
    id: str
    title: str
    description: str
    difficulty: DifficultyLevel
    category: ProblemCategory
    time_limit_seconds: int = 3600  # Default to 1 hour
    memory_limit_mb: int = 128
    test_cases: List[TestCase] = Field(default_factory=list)
    solution: Optional[str] = None
    hints: List[str] = Field(default_factory=list)
    related_problems: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ProblemAttempt(BaseModel):
    """
    Represents an attempt to solve an interview problem.
    """
    problem_id: str
    start_time: float
    end_time: Optional[float] = None
    code: str = ""
    is_completed: bool = False
    is_correct: bool = False
    execution_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    passed_test_cases: int = 0
    total_test_cases: int = 0
    runtime_error: Optional[str] = None
    
    def complete(self, is_correct: bool, execution_time_ms: Optional[float] = None,
                memory_usage_mb: Optional[float] = None, passed_test_cases: int = 0,
                total_test_cases: int = 0, runtime_error: Optional[str] = None) -> None:
        """
        Mark the attempt as complete with results.
        
        Args:
            is_correct: Whether the solution is correct
            execution_time_ms: Execution time in milliseconds
            memory_usage_mb: Memory usage in megabytes
            passed_test_cases: Number of test cases passed
            total_test_cases: Total number of test cases
            runtime_error: Runtime error message, if any
        """
        self.end_time = time.time()
        self.is_completed = True
        self.is_correct = is_correct
        self.execution_time_ms = execution_time_ms
        self.memory_usage_mb = memory_usage_mb
        self.passed_test_cases = passed_test_cases
        self.total_test_cases = total_test_cases
        self.runtime_error = runtime_error
    
    def duration_seconds(self) -> float:
        """
        Get the duration of the attempt in seconds.
        
        Returns:
            Duration of the attempt, or -1 if not completed
        """
        if self.end_time is None:
            if self.is_completed:
                return -1
            else:
                return time.time() - self.start_time
        
        return self.end_time - self.start_time


class TestResult(BaseModel):
    """
    Represents the result of running a test case.
    """
    test_case_index: int
    passed: bool
    actual_output: str
    expected_output: str
    execution_time_ms: float
    memory_usage_mb: float
    error_message: Optional[str] = None


class SolutionAnalysis(BaseModel):
    """
    Represents an analysis of a solution to an interview problem.
    """
    time_complexity: str
    space_complexity: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    optimization_suggestions: List[str] = Field(default_factory=list)
    alternative_approaches: List[str] = Field(default_factory=list)


class InterviewStats(BaseModel):
    """
    Tracks a user's interview preparation statistics.
    """
    problems_attempted: Set[str] = Field(default_factory=set)
    problems_solved: Set[str] = Field(default_factory=set)
    total_time_spent_seconds: float = 0
    attempts_by_difficulty: Dict[str, int] = Field(default_factory=dict)
    attempts_by_category: Dict[str, int] = Field(default_factory=dict)
    
    def add_attempt(self, attempt: ProblemAttempt, problem: InterviewProblem) -> None:
        """
        Add an attempt to the statistics.
        
        Args:
            attempt: The ProblemAttempt to add
            problem: The InterviewProblem that was attempted
        """
        self.problems_attempted.add(attempt.problem_id)
        
        if attempt.is_correct:
            self.problems_solved.add(attempt.problem_id)
            
        # Update time spent
        if attempt.end_time is not None:
            self.total_time_spent_seconds += attempt.duration_seconds()
            
        # Update difficulty stats
        difficulty = problem.difficulty.value
        if difficulty not in self.attempts_by_difficulty:
            self.attempts_by_difficulty[difficulty] = 0
        self.attempts_by_difficulty[difficulty] += 1
        
        # Update category stats
        category = problem.category.value
        if category not in self.attempts_by_category:
            self.attempts_by_category[category] = 0
        self.attempts_by_category[category] += 1
    
    def get_success_rate(self) -> float:
        """
        Get the overall success rate.
        
        Returns:
            Success rate as a percentage (0-100)
        """
        if not self.problems_attempted:
            return 0.0
            
        return (len(self.problems_solved) / len(self.problems_attempted)) * 100
    
    def get_success_rate_by_difficulty(self, difficulty: DifficultyLevel) -> float:
        """
        Get the success rate for a specific difficulty level.
        
        Args:
            difficulty: The difficulty level to check
            
        Returns:
            Success rate as a percentage (0-100)
        """
        # This would require tracking more detailed statistics
        # For now, we'll just return the overall success rate
        return self.get_success_rate()
    
    def get_success_rate_by_category(self, category: ProblemCategory) -> float:
        """
        Get the success rate for a specific problem category.
        
        Args:
            category: The problem category to check
            
        Returns:
            Success rate as a percentage (0-100)
        """
        # This would require tracking more detailed statistics
        # For now, we'll just return the overall success rate
        return self.get_success_rate()
    
    def get_average_time_per_problem(self) -> float:
        """
        Get the average time spent per problem in seconds.
        
        Returns:
            Average time in seconds
        """
        if not self.problems_attempted:
            return 0.0
            
        return self.total_time_spent_seconds / len(self.problems_attempted)