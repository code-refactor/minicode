import time
from uuid import uuid4, UUID

import pytest

from researchtrack.task_management.models import TaskPriority, TaskStatus
from researchtrack.task_management.service import TaskManagementService
from researchtrack.task_management.storage import InMemoryTaskStorage


class TestTaskManagementPerformance:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryTaskStorage()
        self.service = TaskManagementService(self.storage)
    
    def test_task_operation_speed(self):
        """Test that individual task operations complete within 50ms."""
        # Create task
        start_time = time.time()
        task_id = self.service.create_task(
            title="Performance test task",
            description="Testing performance of task operations",
        )
        create_time = time.time() - start_time
        
        # Get task
        start_time = time.time()
        self.service.get_task(task_id)
        get_time = time.time() - start_time
        
        # Update task
        start_time = time.time()
        self.service.update_task(
            task_id=task_id,
            title="Updated performance test task",
            priority=TaskPriority.HIGH,
        )
        update_time = time.time() - start_time
        
        # Delete task
        start_time = time.time()
        self.service.delete_task(task_id)
        delete_time = time.time() - start_time
        
        # Assert all operations completed within 50ms (0.05s)
        assert create_time < 0.05, f"Create operation took {create_time:.6f}s, exceeding 50ms limit"
        assert get_time < 0.05, f"Get operation took {get_time:.6f}s, exceeding 50ms limit"
        assert update_time < 0.05, f"Update operation took {update_time:.6f}s, exceeding 50ms limit"
        assert delete_time < 0.05, f"Delete operation took {delete_time:.6f}s, exceeding 50ms limit"
    
    def test_large_task_list_performance(self):
        """Test performance with 1000+ tasks."""
        # Create 1000 tasks
        task_ids = []
        
        start_time = time.time()
        for i in range(1000):
            task_id = self.service.create_task(
                title=f"Task {i}",
                description=f"Description for task {i}",
                status=TaskStatus.PLANNED if i % 3 == 0 else (
                    TaskStatus.IN_PROGRESS if i % 3 == 1 else TaskStatus.COMPLETED
                ),
                priority=TaskPriority.LOW if i % 4 == 0 else (
                    TaskPriority.MEDIUM if i % 4 == 1 else (
                        TaskPriority.HIGH if i % 4 == 2 else TaskPriority.CRITICAL
                    )
                ),
            )
            task_ids.append(task_id)
            
            # Add tags to some tasks
            if i % 5 == 0:
                self.service.add_task_tag(task_id, "tag1")
            if i % 7 == 0:
                self.service.add_task_tag(task_id, "tag2")
            if i % 11 == 0:
                self.service.add_task_tag(task_id, "tag3")
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / 1000
        
        # Test listing with various filters
        start_time = time.time()
        planned_tasks = self.service.list_tasks(status=TaskStatus.PLANNED)
        filter_by_status_time = time.time() - start_time
        
        start_time = time.time()
        high_priority_tasks = self.service.list_tasks(priority=TaskPriority.HIGH)
        filter_by_priority_time = time.time() - start_time
        
        start_time = time.time()
        tag1_tasks = self.service.list_tasks(tags={"tag1"})
        filter_by_tag_time = time.time() - start_time
        
        start_time = time.time()
        complex_filter_tasks = self.service.list_tasks(
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            tags={"tag3"},
        )
        complex_filter_time = time.time() - start_time
        
        # Test getting and updating random tasks
        get_times = []
        update_times = []
        for i in range(100):  # Test with 100 random tasks
            task_id = task_ids[i * 10]  # Spread across the 1000 tasks
            
            start_time = time.time()
            self.service.get_task(task_id)
            get_times.append(time.time() - start_time)
            
            start_time = time.time()
            self.service.update_task(
                task_id=task_id,
                title=f"Updated Task {i * 10}",
                description=f"Updated description for task {i * 10}",
            )
            update_times.append(time.time() - start_time)
        
        avg_get_time = sum(get_times) / len(get_times)
        avg_update_time = sum(update_times) / len(update_times)
        
        # Assert performance metrics
        assert avg_creation_time < 0.05, f"Average task creation took {avg_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_get_time < 0.05, f"Average task retrieval took {avg_get_time:.6f}s, exceeding 50ms limit"
        assert avg_update_time < 0.05, f"Average task update took {avg_update_time:.6f}s, exceeding 50ms limit"
        
        assert filter_by_status_time < 0.1, f"Filtering by status took {filter_by_status_time:.6f}s, exceeding reasonable limit"
        assert filter_by_priority_time < 0.1, f"Filtering by priority took {filter_by_priority_time:.6f}s, exceeding reasonable limit"
        assert filter_by_tag_time < 0.1, f"Filtering by tag took {filter_by_tag_time:.6f}s, exceeding reasonable limit"
        assert complex_filter_time < 0.1, f"Complex filtering took {complex_filter_time:.6f}s, exceeding reasonable limit"
    
    def test_research_question_hierarchy_performance(self):
        """Test performance with complex research question hierarchies."""
        # Create a tree of research questions (3 levels, branching factor of 5)
        start_time = time.time()
        
        # Create root questions
        root_ids = []
        for i in range(5):
            root_id = self.service.create_research_question(
                text=f"Root question {i}",
                description=f"Top-level research question {i}",
            )
            root_ids.append(root_id)
        
        # Create level 2 questions (children of root)
        level2_ids = []
        for root_id in root_ids:
            for i in range(5):
                level2_id = self.service.create_research_question(
                    text=f"Level 2 question under {root_id} - {i}",
                    description=f"Second-level research question {i}",
                    parent_question_id=root_id,
                )
                level2_ids.append(level2_id)
        
        # Create level 3 questions (children of level 2)
        level3_ids = []
        for level2_id in level2_ids:
            for i in range(5):
                level3_id = self.service.create_research_question(
                    text=f"Level 3 question under {level2_id} - {i}",
                    description=f"Third-level research question {i}",
                    parent_question_id=level2_id,
                )
                level3_ids.append(level3_id)
        
        # Total: 5 + 25 + 125 = 155 questions
        creation_time = time.time() - start_time
        avg_question_creation_time = creation_time / 155
        
        # Test querying the hierarchy
        query_times = []
        for root_id in root_ids:
            start_time = time.time()
            level2_children = self.service.list_research_questions(parent_question_id=root_id)
            query_times.append(time.time() - start_time)
            
            # Verify each root has 5 children
            assert len(level2_children) == 5
        
        # Test more complex queries
        start_time = time.time()
        all_questions = self.service.list_research_questions()
        list_all_time = time.time() - start_time
        
        start_time = time.time()
        top_level = self.service.list_research_questions(parent_question_id=None)
        list_top_time = time.time() - start_time
        
        avg_query_time = sum(query_times) / len(query_times)
        
        # Assert performance metrics
        assert avg_question_creation_time < 0.05, f"Average question creation took {avg_question_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_query_time < 0.05, f"Average hierarchy query took {avg_query_time:.6f}s, exceeding 50ms limit"
        assert list_all_time < 0.1, f"Listing all questions took {list_all_time:.6f}s, exceeding reasonable limit"
        assert list_top_time < 0.05, f"Listing top-level questions took {list_top_time:.6f}s, exceeding 50ms limit"
    
    def test_task_question_association_performance(self):
        """Test performance with many task-question associations."""
        # Create 100 questions and 500 tasks, with multiple associations
        questions = []
        tasks = []
        
        start_time = time.time()
        
        # Create questions
        for i in range(100):
            question_id = self.service.create_research_question(
                text=f"Research question {i}",
                description=f"Description for question {i}",
            )
            questions.append(question_id)
        
        # Create tasks with multiple question associations
        for i in range(500):
            task_id = self.service.create_task(
                title=f"Task {i}",
                description=f"Description for task {i}",
            )
            tasks.append(task_id)
            
            # Associate each task with 1-5 questions
            num_associations = (i % 5) + 1
            for j in range(num_associations):
                # Pick a question based on a formula to ensure distribution
                question_index = (i + j * 17) % 100  # Use a prime number for better distribution
                question_id = questions[question_index]
                self.service.associate_task_with_research_question(task_id, question_id)
        
        setup_time = time.time() - start_time
        
        # Test query performance
        query_times = []
        for i in range(20):  # Test with 20 random questions
            question_id = questions[i * 5]
            
            start_time = time.time()
            related_tasks = self.service.get_tasks_by_research_question(question_id)
            query_times.append(time.time() - start_time)
        
        avg_query_time = sum(query_times) / len(query_times)
        
        # Test filtering tasks by question
        filter_times = []
        for i in range(20):  # Test with 20 random questions
            question_id = questions[i * 5]
            
            start_time = time.time()
            filtered_tasks = self.service.list_tasks(research_question_id=question_id)
            filter_times.append(time.time() - start_time)
            
            # Verify that filtering gives the same result as direct query
            direct_query = self.service.get_tasks_by_research_question(question_id)
            assert set(task.id for task in filtered_tasks) == set(task.id for task in direct_query)
        
        avg_filter_time = sum(filter_times) / len(filter_times)
        
        # Assert performance metrics
        assert avg_query_time < 0.05, f"Average question-task query took {avg_query_time:.6f}s, exceeding 50ms limit"
        assert avg_filter_time < 0.05, f"Average question-based filtering took {avg_filter_time:.6f}s, exceeding 50ms limit"