"""
Interview preparation manager for the text editor.
"""
from typing import Dict, List, Set, Optional, Any, Tuple
from pydantic import BaseModel, Field
import time
import io
import sys
import traceback
import memory_profiler
import re

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


class InterviewManager(BaseModel):
    """
    Manages the interview preparation system.
    
    This class provides functionality for practicing interview problems,
    testing solutions, and tracking progress.
    """
    current_attempt: Optional[ProblemAttempt] = None
    attempts_history: Dict[str, List[ProblemAttempt]] = Field(default_factory=dict)
    stats: InterviewStats = Field(default_factory=InterviewStats)
    
    def get_problem(self, problem_id: str) -> Optional[InterviewProblem]:
        """
        Get a specific interview problem by ID.
        
        Args:
            problem_id: ID of the problem to retrieve
            
        Returns:
            The InterviewProblem object, or None if not found
        """
        return get_problem(problem_id)
    
    def get_all_problems(self) -> List[InterviewProblem]:
        """
        Get all available interview problems.
        
        Returns:
            List of all InterviewProblem objects
        """
        return get_all_problems()
    
    def get_problems_by_difficulty(self, difficulty: DifficultyLevel) -> List[InterviewProblem]:
        """
        Get problems filtered by difficulty.
        
        Args:
            difficulty: Difficulty level to filter by
            
        Returns:
            List of InterviewProblem objects at the specified difficulty
        """
        return get_problems_by_difficulty(difficulty)
    
    def get_problems_by_category(self, category: ProblemCategory) -> List[InterviewProblem]:
        """
        Get problems filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of InterviewProblem objects in the specified category
        """
        return get_problems_by_category(category)
    
    def start_attempt(self, problem_id: str) -> Optional[ProblemAttempt]:
        """
        Start a new attempt at a problem.
        
        Args:
            problem_id: ID of the problem to attempt
            
        Returns:
            The ProblemAttempt object, or None if the problem doesn't exist
        """
        problem = self.get_problem(problem_id)
        if not problem:
            return None
            
        # Create a new attempt
        attempt = ProblemAttempt(
            problem_id=problem_id,
            start_time=time.time()
        )
        
        # Set as the current attempt
        self.current_attempt = attempt
        
        return attempt
    
    def submit_solution(self, code: str) -> Dict[str, Any]:
        """
        Submit a solution for the current problem attempt.
        
        Args:
            code: The solution code
            
        Returns:
            Dictionary with results
        """
        if not self.current_attempt:
            return {"error": "No active attempt"}
            
        problem = self.get_problem(self.current_attempt.problem_id)
        if not problem:
            return {"error": "Problem not found"}
            
        # Update the attempt with the submitted code
        self.current_attempt.code = code
        
        # Run the test cases
        results = self._run_tests(problem, code)
        
        # Extract metrics
        execution_time_ms = 0
        memory_usage_mb = 0
        passed_test_cases = 0
        total_test_cases = len(results)
        runtime_error = None
        
        for result in results:
            if result.passed:
                passed_test_cases += 1
                
            execution_time_ms += result.execution_time_ms
            memory_usage_mb = max(memory_usage_mb, result.memory_usage_mb)
            
            if result.error_message and not runtime_error:
                runtime_error = result.error_message
                
        # Calculate average execution time
        if total_test_cases > 0:
            execution_time_ms /= total_test_cases
            
        # Determine if the solution is correct
        is_correct = passed_test_cases == total_test_cases
        
        # Complete the attempt
        self.current_attempt.complete(
            is_correct=is_correct,
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            passed_test_cases=passed_test_cases,
            total_test_cases=total_test_cases,
            runtime_error=runtime_error
        )
        
        # Add to history
        if problem.id not in self.attempts_history:
            self.attempts_history[problem.id] = []
        self.attempts_history[problem.id].append(self.current_attempt)
        
        # Update stats
        self.stats.add_attempt(self.current_attempt, problem)
        
        # Prepare the response
        response = {
            "problem_id": problem.id,
            "is_correct": is_correct,
            "passed_test_cases": passed_test_cases,
            "total_test_cases": total_test_cases,
            "execution_time_ms": execution_time_ms,
            "memory_usage_mb": memory_usage_mb,
            "runtime_error": runtime_error,
            "test_results": [result.dict() for result in results]
        }
        
        # Add solution analysis if the solution is correct
        if is_correct:
            analysis = self._analyze_solution(problem, code)
            response["analysis"] = analysis.dict()
            
        # Reset the current attempt
        self.current_attempt = None
        
        return response
    
    def _run_tests(self, problem: InterviewProblem, code: str) -> List[TestResult]:
        """
        Run all test cases for a problem.
        
        Args:
            problem: The problem to test
            code: The solution code
            
        Returns:
            List of TestResult objects
        """
        results = []
        
        # Create or identify the required function
        # Extract the function name from the problem description
        function_match = re.search(r'def\s+(\w+)\s*\(', problem.description)
        if not function_match:
            raise ValueError("Could not identify function name in problem description")
            
        function_name = function_match.group(1)
        
        # Create required helper functions for testing
        helper_functions = self._create_helper_functions(problem)
        
        for i, test_case in enumerate(problem.test_cases):
            # Prepare the execution environment
            local_env = {}
            
            # Add helper functions to the environment
            exec(helper_functions, local_env)
            
            try:
                # Measure execution time and memory usage
                start_time = time.time()
                
                # Execute the solution code to define the function
                exec(code, local_env)
                
                # Prepare the test case input
                test_input = test_case.input
                
                # Create code to execute the function with the test input
                test_code = f"result = {function_name}({test_input.split('=')[1].strip()})"
                
                # Track memory usage
                memory_usage_before = memory_profiler.memory_usage()[0]
                
                # Execute the test
                exec(test_code, local_env)
                
                # Calculate metrics
                execution_time_ms = (time.time() - start_time) * 1000
                memory_usage_mb = memory_profiler.memory_usage()[0] - memory_usage_before
                
                # Get the result
                actual_output = str(local_env.get("result"))
                
                # Compare with expected output
                passed = self._compare_outputs(actual_output, test_case.expected_output)
                
                results.append(
                    TestResult(
                        test_case_index=i,
                        passed=passed,
                        actual_output=actual_output,
                        expected_output=test_case.expected_output,
                        execution_time_ms=execution_time_ms,
                        memory_usage_mb=memory_usage_mb
                    )
                )
            except Exception as e:
                # Capture any errors
                error_details = traceback.format_exc()
                
                results.append(
                    TestResult(
                        test_case_index=i,
                        passed=False,
                        actual_output="Error",
                        expected_output=test_case.expected_output,
                        execution_time_ms=0,
                        memory_usage_mb=0,
                        error_message=f"{str(e)}\n{error_details}"
                    )
                )
                
        return results
    
    def _create_helper_functions(self, problem: InterviewProblem) -> str:
        """
        Create helper functions needed for testing the problem.
        
        Args:
            problem: The problem being tested
            
        Returns:
            String containing Python code for helper functions
        """
        # Common imports
        helper_code = """
from typing import List, Optional, Dict, Any
"""
        
        # Add problem-specific helper functions
        if problem.category == ProblemCategory.LINKED_LISTS:
            helper_code += """
# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
        
def create_linked_list(values):
    if not values:
        return None
        
    head = ListNode(values[0])
    current = head
    
    for val in values[1:]:
        current.next = ListNode(val)
        current = current.next
        
    return head
    
def linked_list_to_list(head):
    values = []
    current = head
    
    while current:
        values.append(current.val)
        current = current.next
        
    return values
"""
        
        elif problem.category == ProblemCategory.TREES:
            helper_code += """
# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
        
def create_binary_tree(values):
    if not values:
        return None
        
    # Create the root node
    root = TreeNode(values[0])
    
    # Use a queue to build the tree level by level
    queue = [root]
    i = 1
    
    while i < len(values):
        node = queue.pop(0)
        
        # Left child
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        
        # Right child
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
        
    return root
"""
        
        return helper_code
    
    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """
        Compare actual and expected outputs for equality.
        
        Args:
            actual: The actual output
            expected: The expected output
            
        Returns:
            True if the outputs are considered equal, False otherwise
        """
        # Try to normalize the outputs for comparison
        
        # Replace single quotes with double quotes for consistency
        actual = actual.replace("'", '"')
        expected = expected.replace("'", '"')
        
        # Try to evaluate the strings as Python expressions
        try:
            actual_value = eval(actual)
            expected_value = eval(expected)
            
            # Check for list equality (order might not matter for some problems)
            if isinstance(actual_value, list) and isinstance(expected_value, list):
                if sorted(actual_value) == sorted(expected_value):
                    return True
            
            return actual_value == expected_value
        except:
            # If evaluation fails, fall back to string comparison
            return actual.strip() == expected.strip()
    
    def _analyze_solution(self, problem: InterviewProblem, code: str) -> SolutionAnalysis:
        """
        Analyze a solution to provide feedback.
        
        Args:
            problem: The problem being solved
            code: The solution code
            
        Returns:
            SolutionAnalysis object with feedback
        """
        # This would be more sophisticated in a real implementation
        # For now, we'll provide some basic analysis
        
        # Check for common patterns to estimate time complexity
        time_complexity = "O(n)"  # Default
        if "for" in code and "for" in code[code.index("for")+3:]:
            time_complexity = "O(n²)"  # Nested loops suggest O(n²)
        elif "sort" in code or "sorted" in code:
            time_complexity = "O(n log n)"  # Sorting operations
        elif "while" not in code and "for" not in code:
            time_complexity = "O(1)"  # No loops might suggest constant time
            
        # Space complexity is harder to estimate automatically
        space_complexity = "O(n)"  # Default
        
        # Basic strengths and weaknesses
        strengths = ["Solution passes all test cases"]
        weaknesses = []
        
        # Check code length
        if len(code.strip().split('\n')) > 20:
            weaknesses.append("Solution is quite verbose. Consider simplifying.")
        else:
            strengths.append("Solution is concise.")
            
        # Check for comments
        if code.count('#') < 2:
            weaknesses.append("Solution could benefit from more comments.")
            
        # Basic optimization suggestions
        if time_complexity in ["O(n²)", "O(n log n)"]:
            optimization_suggestions = ["Consider if there's a more efficient algorithm."]
        else:
            optimization_suggestions = ["Time complexity looks good."]
            
        # Add space optimization suggestion if needed
        if "append" in code or "extend" in code:
            optimization_suggestions.append("Check if you can reduce space usage by avoiding growing lists.")
            
        # Alternative approaches
        alternative_approaches = []
        if problem.difficulty == DifficultyLevel.EASY:
            if "recursion" in code.lower() or "def " in code[code.index("def ")+4:]:
                alternative_approaches.append("Consider an iterative approach, which might be more efficient.")
            else:
                alternative_approaches.append("A recursive approach might be more elegant for this problem.")
                
        return SolutionAnalysis(
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            strengths=strengths,
            weaknesses=weaknesses,
            optimization_suggestions=optimization_suggestions,
            alternative_approaches=alternative_approaches
        )
    
    def get_attempt_history(self, problem_id: Optional[str] = None) -> List[ProblemAttempt]:
        """
        Get the history of attempts.
        
        Args:
            problem_id: ID of the problem to filter by (optional)
            
        Returns:
            List of ProblemAttempt objects
        """
        if problem_id:
            return self.attempts_history.get(problem_id, [])
        else:
            # Flatten the dictionary of attempts
            return [attempt for attempts in self.attempts_history.values() for attempt in attempts]
    
    def get_problem_solution(self, problem_id: str) -> Optional[str]:
        """
        Get the solution for a problem.
        
        Args:
            problem_id: ID of the problem to get solution for
            
        Returns:
            The solution code, or None if the problem doesn't exist
        """
        problem = self.get_problem(problem_id)
        if not problem:
            return None
            
        return problem.solution
    
    def get_problem_hints(self, problem_id: str, hint_index: Optional[int] = None) -> Optional[Any]:
        """
        Get hints for a problem.
        
        Args:
            problem_id: ID of the problem to get hints for
            hint_index: Index of the specific hint to get (optional)
            
        Returns:
            List of hints, a specific hint, or None if the problem doesn't exist
        """
        problem = self.get_problem(problem_id)
        if not problem:
            return None
            
        if hint_index is not None:
            if 0 <= hint_index < len(problem.hints):
                return problem.hints[hint_index]
            else:
                return None
        else:
            return problem.hints
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about interview preparation progress.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "problems_attempted": len(self.stats.problems_attempted),
            "problems_solved": len(self.stats.problems_solved),
            "success_rate": self.stats.get_success_rate(),
            "total_time_spent_hours": self.stats.total_time_spent_seconds / 3600,
            "average_time_per_problem_minutes": self.stats.get_average_time_per_problem() / 60,
            "attempts_by_difficulty": self.stats.attempts_by_difficulty,
            "attempts_by_category": self.stats.attempts_by_category
        }
    
    def reset_stats(self) -> None:
        """Reset all interview statistics."""
        self.stats = InterviewStats()
        self.attempts_history = {}