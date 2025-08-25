"""
Database of interview problems for practice.
"""
from typing import Dict, List, Optional

from text_editor.interview.models import (
    InterviewProblem,
    DifficultyLevel,
    ProblemCategory,
    TestCase
)


# Dictionary of sample interview problems
SAMPLE_PROBLEMS = {
    "two_sum": InterviewProblem(
        id="two_sum",
        title="Two Sum",
        description="""
Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example:
```
Input: nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].
```

Write a function:
```python
def two_sum(nums: List[int], target: int) -> List[int]:
    # Your code here
```
""",
        difficulty=DifficultyLevel.EASY,
        category=ProblemCategory.ARRAYS,
        time_limit_seconds=60,  # 1 minute
        test_cases=[
            TestCase(
                input="nums = [2, 7, 11, 15], target = 9",
                expected_output="[0, 1]",
                explanation="nums[0] + nums[1] = 2 + 7 = 9"
            ),
            TestCase(
                input="nums = [3, 2, 4], target = 6",
                expected_output="[1, 2]",
                explanation="nums[1] + nums[2] = 2 + 4 = 6"
            ),
            TestCase(
                input="nums = [3, 3], target = 6",
                expected_output="[0, 1]",
                explanation="nums[0] + nums[1] = 3 + 3 = 6"
            ),
            TestCase(
                input="nums = [1, 2, 3, 4, 5], target = 9",
                expected_output="[3, 4]",
                explanation="nums[3] + nums[4] = 4 + 5 = 9"
            ),
            TestCase(
                input="nums = [5, 2, 3, 1, 5], target = 10",
                expected_output="[0, 4]",
                explanation="nums[0] + nums[4] = 5 + 5 = 10"
            ),
        ],
        solution="""
def two_sum(nums: List[int], target: int) -> List[int]:
    # Create a dictionary to store the complement of each number and its index
    complement_map = {}
    
    # Iterate through the array
    for i, num in enumerate(nums):
        # Calculate the complement (the number we need to find)
        complement = target - num
        
        # Check if the complement is already in our map
        if complement in complement_map:
            # If found, return the indices of the two numbers
            return [complement_map[complement], i]
        
        # If not found, add the current number and its index to the map
        complement_map[num] = i
    
    # If no solution is found (though the problem states one exists)
    return []
""",
        hints=[
            "Can you solve this in one pass through the array?",
            "Consider using a hash map to store values you've seen and their indices.",
            "For each number, check if its complement (target - number) exists in the hash map."
        ],
        tags=["hash-table", "array"]
    ),
    
    "valid_parentheses": InterviewProblem(
        id="valid_parentheses",
        title="Valid Parentheses",
        description="""
Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.

Example 1:
```
Input: s = "()"
Output: true
```

Example 2:
```
Input: s = "()[]{}"
Output: true
```

Example 3:
```
Input: s = "(]"
Output: false
```

Write a function:
```python
def is_valid(s: str) -> bool:
    # Your code here
```
""",
        difficulty=DifficultyLevel.EASY,
        category=ProblemCategory.STRINGS,
        time_limit_seconds=60,  # 1 minute
        test_cases=[
            TestCase(
                input='s = "()"',
                expected_output="True",
                explanation="The parentheses are correctly matched."
            ),
            TestCase(
                input='s = "()[]{}"',
                expected_output="True",
                explanation="All brackets are correctly matched and closed in the correct order."
            ),
            TestCase(
                input='s = "(]"',
                expected_output="False",
                explanation="The closing bracket ] doesn't match the opening bracket (."
            ),
            TestCase(
                input='s = "([)]"',
                expected_output="False",
                explanation="The brackets must be closed in the correct order."
            ),
            TestCase(
                input='s = "{[]}"',
                expected_output="True",
                explanation="The brackets are nested correctly."
            ),
        ],
        solution="""
def is_valid(s: str) -> bool:
    # Create a stack to keep track of opening brackets
    stack = []
    
    # Define a mapping of closing brackets to their opening counterparts
    bracket_map = {
        ')': '(',
        '}': '{',
        ']': '['
    }
    
    # Iterate through each character in the string
    for char in s:
        # If the character is a closing bracket
        if char in bracket_map:
            # Pop the top element from the stack if it's not empty, otherwise assign a dummy value
            top_element = stack.pop() if stack else '#'
            
            # Check if the popped element matches the corresponding opening bracket
            if bracket_map[char] != top_element:
                return False
        else:
            # If the character is an opening bracket, push it onto the stack
            stack.append(char)
    
    # If the stack is empty, all brackets have been matched and closed in the correct order
    return len(stack) == 0
""",
        hints=[
            "Consider using a stack data structure.",
            "Push opening brackets onto the stack.",
            "When you encounter a closing bracket, check if it matches the most recent opening bracket."
        ],
        tags=["stack", "string"]
    ),
    
    "reverse_linked_list": InterviewProblem(
        id="reverse_linked_list",
        title="Reverse Linked List",
        description="""
Given the head of a singly linked list, reverse the list, and return the reversed list.

Example 1:
```
Input: head = [1, 2, 3, 4, 5]
Output: [5, 4, 3, 2, 1]
```

Example 2:
```
Input: head = [1, 2]
Output: [2, 1]
```

Example 3:
```
Input: head = []
Output: []
```

Note: For this problem, we'll represent the linked list as a list of values.

Write a function:
```python
# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_list(head: ListNode) -> ListNode:
    # Your code here
```
""",
        difficulty=DifficultyLevel.EASY,
        category=ProblemCategory.LINKED_LISTS,
        time_limit_seconds=60,  # 1 minute
        test_cases=[
            TestCase(
                input="head = create_linked_list([1, 2, 3, 4, 5])",
                expected_output="[5, 4, 3, 2, 1]",
                explanation="The list is reversed: 1->2->3->4->5 becomes 5->4->3->2->1"
            ),
            TestCase(
                input="head = create_linked_list([1, 2])",
                expected_output="[2, 1]",
                explanation="The list is reversed: 1->2 becomes 2->1"
            ),
            TestCase(
                input="head = create_linked_list([])",
                expected_output="[]",
                explanation="An empty list remains empty when reversed"
            ),
        ],
        solution="""
def reverse_list(head: ListNode) -> ListNode:
    # Initialize previous pointer as None
    prev = None
    # Initialize current pointer as head
    current = head
    
    # Iterate until current becomes None
    while current:
        # Save the next node before changing it
        next_temp = current.next
        # Reverse the link
        current.next = prev
        # Move prev and current one step forward
        prev = current
        current = next_temp
    
    # prev is the new head of the reversed list
    return prev
""",
        hints=[
            "Try to visualize the linked list reversal on paper first.",
            "You'll need to track the previous, current, and next nodes during the reversal.",
            "Be careful about edge cases like an empty list or a list with only one node."
        ],
        tags=["linked-list", "recursion"]
    ),
    
    "maximum_subarray": InterviewProblem(
        id="maximum_subarray",
        title="Maximum Subarray",
        description="""
Given an integer array `nums`, find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.

Example 1:
```
Input: nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
Output: 6
Explanation: [4, -1, 2, 1] has the largest sum = 6.
```

Example 2:
```
Input: nums = [1]
Output: 1
```

Example 3:
```
Input: nums = [5, 4, -1, 7, 8]
Output: 23
```

Write a function:
```python
def max_subarray(nums: List[int]) -> int:
    # Your code here
```
""",
        difficulty=DifficultyLevel.MEDIUM,
        category=ProblemCategory.DYNAMIC_PROGRAMMING,
        time_limit_seconds=120,  # 2 minutes
        test_cases=[
            TestCase(
                input="nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]",
                expected_output="6",
                explanation="The subarray [4, -1, 2, 1] has the largest sum: 6"
            ),
            TestCase(
                input="nums = [1]",
                expected_output="1",
                explanation="The array contains only one element, so the max subarray is the element itself"
            ),
            TestCase(
                input="nums = [5, 4, -1, 7, 8]",
                expected_output="23",
                explanation="The entire array has the largest sum: 23"
            ),
            TestCase(
                input="nums = [-1]",
                expected_output="-1",
                explanation="The array contains only one negative element"
            ),
            TestCase(
                input="nums = [-2, -1]",
                expected_output="-1",
                explanation="The subarray [-1] has the largest sum: -1"
            ),
        ],
        solution="""
def max_subarray(nums: List[int]) -> int:
    # Initialize current_sum and max_sum with the first element
    if not nums:
        return 0
        
    current_sum = max_sum = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # For each element, decide if we should start a new subarray
        # or extend the existing one
        current_sum = max(num, current_sum + num)
        # Update max_sum if current_sum is greater
        max_sum = max(max_sum, current_sum)
    
    return max_sum
""",
        hints=[
            "Consider using Kadane's algorithm for this problem.",
            "At each position, you have two choices: start a new subarray or extend the current one.",
            "Keep track of the maximum sum you've seen so far."
        ],
        tags=["array", "dynamic-programming", "divide-and-conquer"]
    ),
    
    "merge_intervals": InterviewProblem(
        id="merge_intervals",
        title="Merge Intervals",
        description="""
Given an array of `intervals` where intervals[i] = [start_i, end_i], merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.

Example 1:
```
Input: intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]
Output: [[1, 6], [8, 10], [15, 18]]
Explanation: Since intervals [1, 3] and [2, 6] overlap, merge them into [1, 6].
```

Example 2:
```
Input: intervals = [[1, 4], [4, 5]]
Output: [[1, 5]]
Explanation: Intervals [1, 4] and [4, 5] are considered overlapping.
```

Write a function:
```python
def merge(intervals: List[List[int]]) -> List[List[int]]:
    # Your code here
```
""",
        difficulty=DifficultyLevel.MEDIUM,
        category=ProblemCategory.ARRAYS,
        time_limit_seconds=120,  # 2 minutes
        test_cases=[
            TestCase(
                input="intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]",
                expected_output="[[1, 6], [8, 10], [15, 18]]",
                explanation="Intervals [1, 3] and [2, 6] overlap and are merged into [1, 6]"
            ),
            TestCase(
                input="intervals = [[1, 4], [4, 5]]",
                expected_output="[[1, 5]]",
                explanation="Intervals [1, 4] and [4, 5] are considered overlapping and are merged"
            ),
            TestCase(
                input="intervals = [[1, 4], [0, 4]]",
                expected_output="[[0, 4]]",
                explanation="Intervals [1, 4] and [0, 4] overlap and are merged into [0, 4]"
            ),
            TestCase(
                input="intervals = [[1, 4], [0, 1]]",
                expected_output="[[0, 4]]",
                explanation="Intervals [1, 4] and [0, 1] overlap and are merged into [0, 4]"
            ),
            TestCase(
                input="intervals = [[1, 4], [5, 6]]",
                expected_output="[[1, 4], [5, 6]]",
                explanation="Intervals [1, 4] and [5, 6] don't overlap and remain separate"
            ),
        ],
        solution="""
def merge(intervals: List[List[int]]) -> List[List[int]]:
    # Sort the intervals by their start time
    intervals.sort(key=lambda x: x[0])
    
    merged = []
    
    for interval in intervals:
        # If the merged list is empty or if the current interval does not
        # overlap with the previous one, append it
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            # If there is an overlap, merge the current and previous intervals
            merged[-1][1] = max(merged[-1][1], interval[1])
    
    return merged
""",
        hints=[
            "Sort the intervals by their start time to make overlaps easier to identify.",
            "After sorting, you can merge overlapping intervals in a single pass.",
            "Consider edge cases like intervals that are fully contained within others."
        ],
        tags=["array", "sorting"]
    ),
    
    "binary_tree_level_order_traversal": InterviewProblem(
        id="binary_tree_level_order_traversal",
        title="Binary Tree Level Order Traversal",
        description="""
Given the root of a binary tree, return the level order traversal of its nodes' values. (i.e., from left to right, level by level).

Example 1:
```
    3
   / \\
  9  20
    /  \\
   15   7

Input: root = [3, 9, 20, null, null, 15, 7]
Output: [[3], [9, 20], [15, 7]]
```

Example 2:
```
Input: root = [1]
Output: [[1]]
```

Example 3:
```
Input: root = []
Output: []
```

Note: For this problem, we'll represent the binary tree as a list of values, with null representing missing nodes.

Write a function:
```python
# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def level_order(root: TreeNode) -> List[List[int]]:
    # Your code here
```
""",
        difficulty=DifficultyLevel.MEDIUM,
        category=ProblemCategory.TREES,
        time_limit_seconds=120,  # 2 minutes
        test_cases=[
            TestCase(
                input="root = create_binary_tree([3, 9, 20, None, None, 15, 7])",
                expected_output="[[3], [9, 20], [15, 7]]",
                explanation="The tree nodes are traversed level by level from left to right"
            ),
            TestCase(
                input="root = create_binary_tree([1])",
                expected_output="[[1]]",
                explanation="A tree with a single node has one level"
            ),
            TestCase(
                input="root = create_binary_tree([])",
                expected_output="[]",
                explanation="An empty tree has no levels"
            ),
        ],
        solution="""
def level_order(root: TreeNode) -> List[List[int]]:
    # If the root is None, return an empty list
    if not root:
        return []
    
    # Use a queue for level-order traversal
    result = []
    queue = [root]
    
    while queue:
        # Get the number of nodes at the current level
        level_size = len(queue)
        level_nodes = []
        
        # Process all nodes at the current level
        for _ in range(level_size):
            node = queue.pop(0)  # Dequeue
            level_nodes.append(node.val)
            
            # Enqueue children
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        
        # Add the current level to the result
        result.append(level_nodes)
    
    return result
""",
        hints=[
            "Use a queue data structure for a breadth-first search approach.",
            "Process the tree level by level, keeping track of all nodes at each level.",
            "For each level, collect all node values before moving to the next level."
        ],
        tags=["tree", "breadth-first-search", "binary-tree"]
    ),
    
    "climbing_stairs": InterviewProblem(
        id="climbing_stairs",
        title="Climbing Stairs",
        description="""
You are climbing a staircase. It takes n steps to reach the top.

Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?

Example 1:
```
Input: n = 2
Output: 2
Explanation: There are two ways to climb to the top.
1. 1 step + 1 step
2. 2 steps
```

Example 2:
```
Input: n = 3
Output: 3
Explanation: There are three ways to climb to the top.
1. 1 step + 1 step + 1 step
2. 1 step + 2 steps
3. 2 steps + 1 step
```

Constraints:
- 1 <= n <= 45

Write a function:
```python
def climb_stairs(n: int) -> int:
    # Your code here
```
""",
        difficulty=DifficultyLevel.EASY,
        category=ProblemCategory.DYNAMIC_PROGRAMMING,
        time_limit_seconds=60,  # 1 minute
        test_cases=[
            TestCase(
                input="n = 2",
                expected_output="2",
                explanation="There are two ways: 1+1 or 2"
            ),
            TestCase(
                input="n = 3",
                expected_output="3",
                explanation="There are three ways: 1+1+1, 1+2, or 2+1"
            ),
            TestCase(
                input="n = 4",
                expected_output="5",
                explanation="There are five ways: 1+1+1+1, 1+1+2, 1+2+1, 2+1+1, or 2+2"
            ),
            TestCase(
                input="n = 5",
                expected_output="8",
                explanation="There are eight ways to climb 5 stairs"
            ),
            TestCase(
                input="n = 1",
                expected_output="1",
                explanation="There is only one way to climb 1 stair: take 1 step"
            ),
        ],
        solution="""
def climb_stairs(n: int) -> int:
    # Base cases
    if n <= 2:
        return n
    
    # Initialize first two numbers in the sequence
    a, b = 1, 2
    
    # Calculate the nth number in the sequence
    for i in range(3, n + 1):
        a, b = b, a + b
    
    return b
""",
        hints=[
            "Try to identify the recurrence relation. How many ways can you reach step n?",
            "The number of ways to reach step n is the sum of ways to reach step n-1 and step n-2.",
            "This is a Fibonacci sequence problem. Can you optimize your solution to use O(1) space?"
        ],
        tags=["dynamic-programming", "math", "memoization"]
    ),
    
    "word_search": InterviewProblem(
        id="word_search",
        title="Word Search",
        description="""
Given an m x n grid of characters `board` and a string `word`, return `true` if `word` exists in the grid.

The word can be constructed from letters of sequentially adjacent cells, where adjacent cells are horizontally or vertically neighboring. The same letter cell may not be used more than once.

Example 1:
```
board = [
  ['A','B','C','E'],
  ['S','F','C','S'],
  ['A','D','E','E']
]
word = "ABCCED"
Output: true
```

Example 2:
```
board = [
  ['A','B','C','E'],
  ['S','F','C','S'],
  ['A','D','E','E']
]
word = "SEE"
Output: true
```

Example 3:
```
board = [
  ['A','B','C','E'],
  ['S','F','C','S'],
  ['A','D','E','E']
]
word = "ABCB"
Output: false
```

Write a function:
```python
def exist(board: List[List[str]], word: str) -> bool:
    # Your code here
```
""",
        difficulty=DifficultyLevel.MEDIUM,
        category=ProblemCategory.GRAPHS,
        time_limit_seconds=180,  # 3 minutes
        test_cases=[
            TestCase(
                input='board = [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]], word = "ABCCED"',
                expected_output="True",
                explanation="The word ABCCED can be constructed from the board"
            ),
            TestCase(
                input='board = [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]], word = "SEE"',
                expected_output="True",
                explanation="The word SEE can be constructed from the board"
            ),
            TestCase(
                input='board = [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]], word = "ABCB"',
                expected_output="False",
                explanation="The word ABCB cannot be constructed from the board (can't reuse the same cell)"
            ),
        ],
        solution="""
def exist(board: List[List[str]], word: str) -> bool:
    if not board or not board[0]:
        return False
    
    rows, cols = len(board), len(board[0])
    
    # Define a recursive DFS function to search from a position
    def dfs(r, c, index):
        # Base case: if we found all characters in the word
        if index == len(word):
            return True
        
        # Check boundaries and if current cell matches the character we're looking for
        if (r < 0 or r >= rows or c < 0 or c >= cols or 
            board[r][c] != word[index]):
            return False
        
        # Mark the cell as visited by changing it to a special character
        temp = board[r][c]
        board[r][c] = '#'
        
        # Explore in all four directions
        found = (dfs(r+1, c, index+1) or 
                 dfs(r-1, c, index+1) or 
                 dfs(r, c+1, index+1) or 
                 dfs(r, c-1, index+1))
        
        # Restore the cell
        board[r][c] = temp
        
        return found
    
    # Try starting from each cell
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == word[0] and dfs(r, c, 0):
                return True
    
    return False
""",
        hints=[
            "Use depth-first search (DFS) or backtracking to explore all possible paths.",
            "Remember to mark visited cells to avoid using the same cell twice.",
            "Consider starting the search from each cell in the board."
        ],
        tags=["array", "backtracking", "matrix"]
    ),
}


def get_problem(problem_id: str) -> Optional[InterviewProblem]:
    """
    Get a specific interview problem by ID.
    
    Args:
        problem_id: ID of the problem to retrieve
        
    Returns:
        The InterviewProblem object, or None if not found
    """
    return SAMPLE_PROBLEMS.get(problem_id)


def get_all_problems() -> List[InterviewProblem]:
    """
    Get all available interview problems.
    
    Returns:
        List of all InterviewProblem objects
    """
    return list(SAMPLE_PROBLEMS.values())


def get_problems_by_difficulty(difficulty: DifficultyLevel) -> List[InterviewProblem]:
    """
    Get problems filtered by difficulty.
    
    Args:
        difficulty: Difficulty level to filter by
        
    Returns:
        List of InterviewProblem objects at the specified difficulty
    """
    return [p for p in SAMPLE_PROBLEMS.values() if p.difficulty == difficulty]


def get_problems_by_category(category: ProblemCategory) -> List[InterviewProblem]:
    """
    Get problems filtered by category.
    
    Args:
        category: Category to filter by
        
    Returns:
        List of InterviewProblem objects in the specified category
    """
    return [p for p in SAMPLE_PROBLEMS.values() if p.category == category]