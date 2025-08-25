"""
Tests for the interview preparation system.
"""
import pytest
import time
import sys
import platform

from text_editor.interview.models import (
    InterviewProblem,
    DifficultyLevel,
    ProblemCategory,
    TestCase,
    ProblemAttempt,
    TestResult,
    SolutionAnalysis,
    InterviewStats
)
from text_editor.interview.problems import (
    get_problem,
    get_all_problems,
    get_problems_by_difficulty,
    get_problems_by_category
)
from text_editor.interview.manager import InterviewManager


class TestInterviewModels:
    def test_interview_problem(self):
        """Test the InterviewProblem model functionality."""
        problem = InterviewProblem(
            id="test_problem",
            title="Test Problem",
            description="A test problem",
            difficulty=DifficultyLevel.EASY,
            category=ProblemCategory.ARRAYS,
            test_cases=[
                TestCase(
                    input="input1",
                    expected_output="output1"
                )
            ]
        )
        
        assert problem.id == "test_problem"
        assert problem.title == "Test Problem"
        assert problem.difficulty == DifficultyLevel.EASY
        assert problem.category == ProblemCategory.ARRAYS
        assert len(problem.test_cases) == 1
    
    def test_problem_attempt(self):
        """Test the ProblemAttempt functionality."""
        attempt = ProblemAttempt(
            problem_id="test_problem",
            start_time=time.time()
        )
        
        assert attempt.problem_id == "test_problem"
        assert attempt.start_time > 0
        assert not attempt.is_completed
        
        # Complete the attempt
        attempt.complete(
            is_correct=True,
            execution_time_ms=100,
            memory_usage_mb=10,
            passed_test_cases=5,
            total_test_cases=5
        )
        
        assert attempt.is_completed
        assert attempt.is_correct
        assert attempt.execution_time_ms == 100
        assert attempt.memory_usage_mb == 10
        assert attempt.passed_test_cases == 5
        assert attempt.total_test_cases == 5
        assert attempt.end_time is not None
        assert attempt.duration_seconds() > 0
    
    def test_test_result(self):
        """Test the TestResult model functionality."""
        result = TestResult(
            test_case_index=0,
            passed=True,
            actual_output="output1",
            expected_output="output1",
            execution_time_ms=100,
            memory_usage_mb=10
        )
        
        assert result.test_case_index == 0
        assert result.passed
        assert result.actual_output == "output1"
        assert result.expected_output == "output1"
        assert result.execution_time_ms == 100
        assert result.memory_usage_mb == 10
    
    def test_solution_analysis(self):
        """Test the SolutionAnalysis model functionality."""
        analysis = SolutionAnalysis(
            time_complexity="O(n)",
            space_complexity="O(1)",
            strengths=["Efficient", "Readable"],
            weaknesses=["Could be more optimized"],
            optimization_suggestions=["Use a hash map"],
            alternative_approaches=["Recursive solution"]
        )
        
        assert analysis.time_complexity == "O(n)"
        assert analysis.space_complexity == "O(1)"
        assert "Efficient" in analysis.strengths
        assert "Could be more optimized" in analysis.weaknesses
        assert "Use a hash map" in analysis.optimization_suggestions
        assert "Recursive solution" in analysis.alternative_approaches
    
    def test_interview_stats(self):
        """Test the InterviewStats functionality."""
        stats = InterviewStats()
        
        # Create a problem attempt
        attempt = ProblemAttempt(
            problem_id="test_problem",
            start_time=time.time() - 100,
            end_time=time.time(),
            is_completed=True,
            is_correct=True
        )
        
        # Create a problem
        problem = InterviewProblem(
            id="test_problem",
            title="Test Problem",
            description="A test problem",
            difficulty=DifficultyLevel.EASY,
            category=ProblemCategory.ARRAYS
        )
        
        # Add the attempt to the stats
        stats.add_attempt(attempt, problem)
        
        assert "test_problem" in stats.problems_attempted
        assert "test_problem" in stats.problems_solved
        assert stats.total_time_spent_seconds > 0
        assert DifficultyLevel.EASY.value in stats.attempts_by_difficulty
        assert ProblemCategory.ARRAYS.value in stats.attempts_by_category
        
        # Test success rate
        assert stats.get_success_rate() == 100.0
        
        # Test average time
        assert stats.get_average_time_per_problem() > 0


class TestInterviewProblems:
    def test_get_problem(self):
        """Test getting a specific problem by ID."""
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        problem = get_problem(problem_id)
        
        assert problem is not None
        assert problem.id == problem_id
        
        # Test with a non-existent problem
        assert get_problem("non_existent") is None
    
    def test_get_all_problems(self):
        """Test getting all problems."""
        problems = get_all_problems()
        
        assert problems
        assert all(isinstance(p, InterviewProblem) for p in problems)
    
    def test_get_problems_by_difficulty(self):
        """Test getting problems filtered by difficulty."""
        difficulty = DifficultyLevel.EASY
        problems = get_problems_by_difficulty(difficulty)
        
        assert problems
        assert all(p.difficulty == difficulty for p in problems)
    
    def test_get_problems_by_category(self):
        """Test getting problems filtered by category."""
        category = ProblemCategory.ARRAYS
        problems = get_problems_by_category(category)
        
        assert problems
        assert all(p.category == category for p in problems)


class TestInterviewManager:
    def test_initialization(self):
        """Test that the interview manager is initialized correctly."""
        manager = InterviewManager()
        
        assert manager.stats is not None
        assert manager.current_attempt is None
        assert isinstance(manager.attempts_history, dict)
    
    def test_get_problem(self):
        """Test getting a specific problem by ID."""
        manager = InterviewManager()
        
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        problem = manager.get_problem(problem_id)
        
        assert problem is not None
        assert problem.id == problem_id
    
    def test_get_all_problems(self):
        """Test getting all problems."""
        manager = InterviewManager()
        problems = manager.get_all_problems()
        
        assert problems
        assert all(isinstance(p, InterviewProblem) for p in problems)
    
    def test_start_attempt(self):
        """Test starting a new attempt at a problem."""
        manager = InterviewManager()
        
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        attempt = manager.start_attempt(problem_id)
        
        assert attempt is not None
        assert attempt.problem_id == problem_id
        assert manager.current_attempt is not None
        
        # Test with a non-existent problem
        assert manager.start_attempt("non_existent") is None
    
    @pytest.mark.skipif(
        condition=platform.system() == "Windows" or sys.platform.startswith("win"),
        reason="Code execution may not work reliably in all CI environments"
    )
    def test_submit_solution(self):
        """Test submitting a solution for a problem."""
        manager = InterviewManager()
        
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        manager.start_attempt(problem_id)
        
        # Submit a correct solution
        solution_code = """
def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []
"""
        
        # Execute the solution submission
        result = manager.submit_solution(solution_code)
        
        # Check the structure of the result
        assert "problem_id" in result
        assert "is_correct" in result
        assert "passed_test_cases" in result
        assert "total_test_cases" in result
        
        # The attempt should be complete and added to history
        assert manager.current_attempt is None
        assert problem_id in manager.attempts_history
    
    def test_get_attempt_history(self):
        """Test getting the history of attempts."""
        manager = InterviewManager()
        
        # Add a sample attempt to history
        problem_id = "two_sum"
        attempt = ProblemAttempt(
            problem_id=problem_id,
            start_time=time.time()
        )
        attempt.complete(True, 100, 10, 5, 5)
        
        manager.attempts_history[problem_id] = [attempt]
        
        # Get all history
        all_history = manager.get_attempt_history()
        assert all_history
        
        # Get history for a specific problem
        problem_history = manager.get_attempt_history(problem_id)
        assert problem_history
        assert problem_history[0].problem_id == problem_id
    
    def test_get_problem_solution(self):
        """Test getting the solution for a problem."""
        manager = InterviewManager()
        
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        solution = manager.get_problem_solution(problem_id)
        
        assert solution is not None
        assert "two_sum" in solution  # Should contain the function name
    
    def test_get_problem_hints(self):
        """Test getting hints for a problem."""
        manager = InterviewManager()
        
        # Choose a problem ID from the default problems
        problem_id = "two_sum"  # This is a default problem
        
        # Get all hints
        hints = manager.get_problem_hints(problem_id)
        assert hints
        
        # Get a specific hint
        hint = manager.get_problem_hints(problem_id, 0)
        assert hint is not None
    
    def test_get_stats(self):
        """Test getting statistics about interview preparation progress."""
        manager = InterviewManager()
        
        # Add a sample attempt to stats
        problem_id = "two_sum"
        attempt = ProblemAttempt(
            problem_id=problem_id,
            start_time=time.time() - 100,
            end_time=time.time(),
            is_completed=True,
            is_correct=True
        )
        
        # Create a problem
        problem = InterviewProblem(
            id=problem_id,
            title="Test Problem",
            description="A test problem",
            difficulty=DifficultyLevel.EASY,
            category=ProblemCategory.ARRAYS
        )
        
        # Add the attempt to the stats
        manager.stats.add_attempt(attempt, problem)
        
        # Get stats
        stats = manager.get_stats()
        
        assert stats["problems_attempted"] == 1
        assert stats["problems_solved"] == 1
        assert stats["success_rate"] == 100.0
    
    def test_reset_stats(self):
        """Test resetting all interview statistics."""
        manager = InterviewManager()
        
        # Add a sample attempt to stats
        problem_id = "two_sum"
        attempt = ProblemAttempt(
            problem_id=problem_id,
            start_time=time.time() - 100,
            end_time=time.time(),
            is_completed=True,
            is_correct=True
        )
        
        # Create a problem
        problem = InterviewProblem(
            id=problem_id,
            title="Test Problem",
            description="A test problem",
            difficulty=DifficultyLevel.EASY,
            category=ProblemCategory.ARRAYS
        )
        
        # Add the attempt to the stats
        manager.stats.add_attempt(attempt, problem)
        manager.attempts_history[problem_id] = [attempt]
        
        # Reset stats
        manager.reset_stats()
        
        assert not manager.stats.problems_attempted
        assert not manager.stats.problems_solved
        assert not manager.attempts_history