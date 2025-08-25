"""Thread execution tracing and visualization."""

import json
from typing import Dict, List, Optional, Set, Tuple, Any, Union


class ExecutionTracer:
    """
    Records and processes thread execution traces.
    
    This module captures various events during VM execution,
    such as thread creation, scheduling, synchronization, and memory access.
    """
    
    def __init__(self):
        """Initialize the execution tracer."""
        # Main trace log
        self.trace_events: List[Dict[str, Any]] = []
        
        # Thread state history
        self.thread_states: Dict[str, List[Dict[str, Any]]] = {}
        
        # Processor assignment history
        self.processor_assignments: Dict[int, List[Dict[str, Any]]] = {}
        
        # Synchronization operation history
        self.sync_operations: List[Dict[str, Any]] = []
        
        # Memory access history
        self.memory_accesses: List[Dict[str, Any]] = []
        
        # Context switch history
        self.context_switches: List[Dict[str, Any]] = []
        
        # Thread wait events
        self.wait_events: List[Dict[str, Any]] = []
        
        # Current timestamp
        self.current_timestamp = 0
    
    def record_event(self, event_type: str, data: Dict[str, Any], timestamp: Optional[int] = None) -> None:
        """
        Record an execution event.
        
        Args:
            event_type: Type of event
            data: Event data
            timestamp: Event timestamp, or None to use current timestamp
        """
        if timestamp is None:
            timestamp = self.current_timestamp
        else:
            # Update current timestamp if a newer one is provided
            self.current_timestamp = max(self.current_timestamp, timestamp)
        
        # Create the event
        event = {
            "type": event_type,
            "timestamp": timestamp,
            **data,
        }
        
        # Add to the main trace
        self.trace_events.append(event)
        
        # Process based on event type
        if event_type == "thread_state_change":
            self._process_thread_state_change(event)
        elif event_type == "processor_assignment":
            self._process_processor_assignment(event)
        elif event_type == "sync_operation":
            self._process_sync_operation(event)
        elif event_type == "memory_access":
            self._process_memory_access(event)
        elif event_type == "context_switch":
            self._process_context_switch(event)
        elif event_type == "thread_wait":
            self._process_thread_wait(event)
    
    def _process_thread_state_change(self, event: Dict[str, Any]) -> None:
        """
        Process a thread state change event.
        
        Args:
            event: The event to process
        """
        thread_id = event["thread_id"]
        
        # Initialize thread history if needed
        if thread_id not in self.thread_states:
            self.thread_states[thread_id] = []
        
        # Add to thread history
        self.thread_states[thread_id].append({
            "timestamp": event["timestamp"],
            "old_state": event["old_state"],
            "new_state": event["new_state"],
            "reason": event.get("reason"),
        })
    
    def _process_processor_assignment(self, event: Dict[str, Any]) -> None:
        """
        Process a processor assignment event.
        
        Args:
            event: The event to process
        """
        processor_id = event["processor_id"]
        
        # Initialize processor history if needed
        if processor_id not in self.processor_assignments:
            self.processor_assignments[processor_id] = []
        
        # Add to processor history
        self.processor_assignments[processor_id].append({
            "timestamp": event["timestamp"],
            "thread_id": event["thread_id"],
            "assignment_type": event.get("assignment_type", "scheduled"),
        })
    
    def _process_sync_operation(self, event: Dict[str, Any]) -> None:
        """
        Process a synchronization operation event.
        
        Args:
            event: The event to process
        """
        # Add to synchronization history
        self.sync_operations.append({
            "timestamp": event["timestamp"],
            "thread_id": event["thread_id"],
            "operation": event["operation"],
            "object_id": event["object_id"],
            "object_type": event["object_type"],
            "success": event.get("success", True),
        })
    
    def _process_memory_access(self, event: Dict[str, Any]) -> None:
        """
        Process a memory access event.
        
        Args:
            event: The event to process
        """
        # Add to memory access history
        self.memory_accesses.append({
            "timestamp": event["timestamp"],
            "thread_id": event["thread_id"],
            "processor_id": event["processor_id"],
            "address": event["address"],
            "access_type": event["access_type"],
            "value": event.get("value"),
            "lock_set": event.get("lock_set", []),
        })
    
    def _process_context_switch(self, event: Dict[str, Any]) -> None:
        """
        Process a context switch event.
        
        Args:
            event: The event to process
        """
        # Add to context switch history
        self.context_switches.append({
            "timestamp": event["timestamp"],
            "processor_id": event["processor_id"],
            "old_thread_id": event["old_thread_id"],
            "new_thread_id": event["new_thread_id"],
            "reason": event.get("reason"),
        })
    
    def _process_thread_wait(self, event: Dict[str, Any]) -> None:
        """
        Process a thread wait event.
        
        Args:
            event: The event to process
        """
        # Add to wait event history
        self.wait_events.append({
            "timestamp": event["timestamp"],
            "thread_id": event["thread_id"],
            "wait_reason": event["wait_reason"],
            "sync_object_id": event.get("sync_object_id"),
            "sync_object_type": event.get("sync_object_type"),
        })
    
    def advance_timestamp(self, increment: int = 1) -> int:
        """
        Advance the current timestamp.
        
        Args:
            increment: Amount to increment the timestamp
            
        Returns:
            The new timestamp
        """
        self.current_timestamp += increment
        return self.current_timestamp
    
    def get_thread_state_at(self, thread_id: str, timestamp: int) -> Optional[str]:
        """
        Get the state of a thread at a specific timestamp.
        
        Args:
            thread_id: ID of the thread
            timestamp: Timestamp to check
            
        Returns:
            Thread state, or None if unknown
        """
        if thread_id not in self.thread_states:
            return None
        
        # Find the most recent state change before or at the timestamp
        latest_state = None
        
        for state_change in self.thread_states[thread_id]:
            if state_change["timestamp"] <= timestamp:
                latest_state = state_change["new_state"]
            else:
                break
        
        return latest_state
    
    def get_processor_assignment_at(
        self, processor_id: int, timestamp: int
    ) -> Optional[str]:
        """
        Get the thread assigned to a processor at a specific timestamp.
        
        Args:
            processor_id: ID of the processor
            timestamp: Timestamp to check
            
        Returns:
            Thread ID, or None if no thread assigned
        """
        if processor_id not in self.processor_assignments:
            return None
        
        # Find the most recent assignment before or at the timestamp
        latest_assignment = None
        
        for assignment in self.processor_assignments[processor_id]:
            if assignment["timestamp"] <= timestamp:
                latest_assignment = assignment["thread_id"]
            else:
                break
        
        return latest_assignment
    
    def get_thread_timeline(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get a timeline of events for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            List of events in chronological order
        """
        # Collect all events for this thread
        thread_events = []
        
        # State changes
        if thread_id in self.thread_states:
            for state_change in self.thread_states[thread_id]:
                thread_events.append({
                    "timestamp": state_change["timestamp"],
                    "event_type": "state_change",
                    "old_state": state_change["old_state"],
                    "new_state": state_change["new_state"],
                    "reason": state_change.get("reason"),
                })
        
        # Processor assignments
        for processor_id, assignments in self.processor_assignments.items():
            for assignment in assignments:
                if assignment["thread_id"] == thread_id:
                    thread_events.append({
                        "timestamp": assignment["timestamp"],
                        "event_type": "processor_assignment",
                        "processor_id": processor_id,
                        "assignment_type": assignment.get("assignment_type", "scheduled"),
                    })
        
        # Synchronization operations
        for op in self.sync_operations:
            if op["thread_id"] == thread_id:
                thread_events.append({
                    "timestamp": op["timestamp"],
                    "event_type": "sync_operation",
                    "operation": op["operation"],
                    "object_id": op["object_id"],
                    "object_type": op["object_type"],
                    "success": op.get("success", True),
                })
        
        # Memory accesses
        for access in self.memory_accesses:
            if access["thread_id"] == thread_id:
                thread_events.append({
                    "timestamp": access["timestamp"],
                    "event_type": "memory_access",
                    "address": access["address"],
                    "access_type": access["access_type"],
                    "value": access.get("value"),
                })
        
        # Context switches
        for switch in self.context_switches:
            if switch["old_thread_id"] == thread_id or switch["new_thread_id"] == thread_id:
                thread_events.append({
                    "timestamp": switch["timestamp"],
                    "event_type": "context_switch",
                    "processor_id": switch["processor_id"],
                    "role": "from" if switch["old_thread_id"] == thread_id else "to",
                    "other_thread_id": (
                        switch["new_thread_id"] if switch["old_thread_id"] == thread_id
                        else switch["old_thread_id"]
                    ),
                    "reason": switch.get("reason"),
                })
        
        # Wait events
        for wait in self.wait_events:
            if wait["thread_id"] == thread_id:
                thread_events.append({
                    "timestamp": wait["timestamp"],
                    "event_type": "wait",
                    "wait_reason": wait["wait_reason"],
                    "sync_object_id": wait.get("sync_object_id"),
                    "sync_object_type": wait.get("sync_object_type"),
                })
        
        # Sort by timestamp
        thread_events.sort(key=lambda e: e["timestamp"])
        
        return thread_events
    
    def get_processor_timeline(self, processor_id: int) -> List[Dict[str, Any]]:
        """
        Get a timeline of events for a specific processor.
        
        Args:
            processor_id: ID of the processor
            
        Returns:
            List of events in chronological order
        """
        # Collect all events for this processor
        processor_events = []
        
        # Processor assignments
        if processor_id in self.processor_assignments:
            for assignment in self.processor_assignments[processor_id]:
                processor_events.append({
                    "timestamp": assignment["timestamp"],
                    "event_type": "thread_assignment",
                    "thread_id": assignment["thread_id"],
                    "assignment_type": assignment.get("assignment_type", "scheduled"),
                })
        
        # Context switches
        for switch in self.context_switches:
            if switch["processor_id"] == processor_id:
                processor_events.append({
                    "timestamp": switch["timestamp"],
                    "event_type": "context_switch",
                    "old_thread_id": switch["old_thread_id"],
                    "new_thread_id": switch["new_thread_id"],
                    "reason": switch.get("reason"),
                })
        
        # Memory accesses
        for access in self.memory_accesses:
            if access.get("processor_id") == processor_id:
                processor_events.append({
                    "timestamp": access["timestamp"],
                    "event_type": "memory_access",
                    "thread_id": access["thread_id"],
                    "address": access["address"],
                    "access_type": access["access_type"],
                    "value": access.get("value"),
                })
        
        # Sort by timestamp
        processor_events.sort(key=lambda e: e["timestamp"])
        
        return processor_events
    
    def get_sync_object_timeline(self, object_type: str, object_id: int) -> List[Dict[str, Any]]:
        """
        Get a timeline of events for a specific synchronization object.
        
        Args:
            object_type: Type of synchronization object
            object_id: ID of the synchronization object
            
        Returns:
            List of events in chronological order
        """
        # Collect all events for this synchronization object
        object_events = []
        
        # Synchronization operations
        for op in self.sync_operations:
            if op["object_type"] == object_type and op["object_id"] == object_id:
                object_events.append({
                    "timestamp": op["timestamp"],
                    "event_type": "sync_operation",
                    "thread_id": op["thread_id"],
                    "operation": op["operation"],
                    "success": op.get("success", True),
                })
        
        # Wait events
        for wait in self.wait_events:
            if (wait.get("sync_object_type") == object_type and
                    wait.get("sync_object_id") == object_id):
                object_events.append({
                    "timestamp": wait["timestamp"],
                    "event_type": "wait",
                    "thread_id": wait["thread_id"],
                    "wait_reason": wait["wait_reason"],
                })
        
        # Sort by timestamp
        object_events.sort(key=lambda e: e["timestamp"])
        
        return object_events
    
    def get_memory_address_timeline(self, address: int) -> List[Dict[str, Any]]:
        """
        Get a timeline of accesses for a specific memory address.
        
        Args:
            address: Memory address
            
        Returns:
            List of memory access events in chronological order
        """
        # Collect all accesses to this address
        address_events = []
        
        for access in self.memory_accesses:
            if access["address"] == address:
                address_events.append({
                    "timestamp": access["timestamp"],
                    "thread_id": access["thread_id"],
                    "processor_id": access.get("processor_id"),
                    "access_type": access["access_type"],
                    "value": access.get("value"),
                    "lock_set": access.get("lock_set", []),
                })
        
        # Sort by timestamp
        address_events.sort(key=lambda e: e["timestamp"])
        
        return address_events
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the trace.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "total_events": len(self.trace_events),
            "thread_count": len(self.thread_states),
            "processor_count": len(self.processor_assignments),
            "sync_operations": len(self.sync_operations),
            "memory_accesses": len(self.memory_accesses),
            "context_switches": len(self.context_switches),
            "wait_events": len(self.wait_events),
            "duration": self.current_timestamp,
        }
    
    def export_trace(self, format: str = "json") -> str:
        """
        Export the trace in a specific format.
        
        Args:
            format: Export format ("json" or "chrome")
            
        Returns:
            Formatted trace string
        """
        if format == "json":
            return json.dumps(self.trace_events, indent=2)
        
        elif format == "chrome":
            # Convert to Chrome tracing format
            chrome_events = []
            
            # Thread activities
            for thread_id, states in self.thread_states.items():
                # Create thread name metadata
                chrome_events.append({
                    "name": "thread_name",
                    "ph": "M",  # Metadata
                    "pid": 1,  # Process ID
                    "tid": int(hash(thread_id) % 10000),  # Thread ID
                    "args": {"name": f"Thread {thread_id}"}
                })
                
                # Create spans for each state
                last_state = None
                last_ts = 0
                
                for i, state in enumerate(states):
                    if last_state:
                        chrome_events.append({
                            "name": last_state,
                            "ph": "X",  # Complete event
                            "pid": 1,
                            "tid": int(hash(thread_id) % 10000),
                            "ts": last_ts,
                            "dur": state["timestamp"] - last_ts,
                            "args": {"state": last_state}
                        })
                    
                    last_state = state["new_state"]
                    last_ts = state["timestamp"]
                
                # Add the final state
                if last_state and last_ts < self.current_timestamp:
                    chrome_events.append({
                        "name": last_state,
                        "ph": "X",
                        "pid": 1,
                        "tid": int(hash(thread_id) % 10000),
                        "ts": last_ts,
                        "dur": self.current_timestamp - last_ts,
                        "args": {"state": last_state}
                    })
            
            # Processor activities
            for processor_id, assignments in self.processor_assignments.items():
                # Create processor name metadata
                chrome_events.append({
                    "name": "thread_name",
                    "ph": "M",
                    "pid": 2,  # Different process for processors
                    "tid": processor_id,
                    "args": {"name": f"Processor {processor_id}"}
                })
                
                # Create spans for each assignment
                last_thread = None
                last_ts = 0
                
                for i, assignment in enumerate(assignments):
                    if last_thread:
                        chrome_events.append({
                            "name": last_thread,
                            "ph": "X",
                            "pid": 2,
                            "tid": processor_id,
                            "ts": last_ts,
                            "dur": assignment["timestamp"] - last_ts,
                            "args": {"thread_id": last_thread}
                        })
                    
                    last_thread = assignment["thread_id"]
                    last_ts = assignment["timestamp"]
                
                # Add the final assignment
                if last_thread and last_ts < self.current_timestamp:
                    chrome_events.append({
                        "name": last_thread,
                        "ph": "X",
                        "pid": 2,
                        "tid": processor_id,
                        "ts": last_ts,
                        "dur": self.current_timestamp - last_ts,
                        "args": {"thread_id": last_thread}
                    })
            
            # Sync operations
            for op in self.sync_operations:
                chrome_events.append({
                    "name": f"{op['object_type']}_{op['operation']}",
                    "ph": "i",  # Instant event
                    "pid": 3,  # Different process for sync operations
                    "tid": int(hash(op["thread_id"]) % 10000),
                    "ts": op["timestamp"],
                    "args": {
                        "thread_id": op["thread_id"],
                        "object_id": op["object_id"],
                        "object_type": op["object_type"],
                        "success": op.get("success", True),
                    }
                })
            
            # Memory accesses
            for access in self.memory_accesses:
                chrome_events.append({
                    "name": f"mem_{access['access_type']}",
                    "ph": "i",
                    "pid": 4,  # Different process for memory accesses
                    "tid": int(hash(access["thread_id"]) % 10000),
                    "ts": access["timestamp"],
                    "args": {
                        "thread_id": access["thread_id"],
                        "address": access["address"],
                        "value": access.get("value"),
                    }
                })
            
            return json.dumps(chrome_events)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_trace(self, trace_str: str, format: str = "json") -> None:
        """
        Import a trace from a string.
        
        Args:
            trace_str: Trace string
            format: Trace format ("json" or "chrome")
        """
        if format == "json":
            events = json.loads(trace_str)
            
            # Clear existing trace
            self.trace_events = []
            self.thread_states = {}
            self.processor_assignments = {}
            self.sync_operations = []
            self.memory_accesses = []
            self.context_switches = []
            self.wait_events = []
            
            # Process each event
            for event in events:
                self.record_event(event["type"], event, event["timestamp"])
        
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def reset(self) -> None:
        """Reset the tracer."""
        self.trace_events = []
        self.thread_states = {}
        self.processor_assignments = {}
        self.sync_operations = []
        self.memory_accesses = []
        self.context_switches = []
        self.wait_events = []
        self.current_timestamp = 0


class TraceVisualizer:
    """
    Visualizes execution traces.
    
    Provides methods to convert execution traces into various visualization formats
    such as ASCII art, HTML, and export formats compatible with external tools.
    """
    
    @staticmethod
    def create_ascii_timeline(tracer: ExecutionTracer, num_cycles: int = 50) -> str:
        """
        Create an ASCII art timeline visualization.
        
        Args:
            tracer: Execution tracer
            num_cycles: Number of cycles to show
            
        Returns:
            ASCII art timeline string
        """
        # Get all unique threads and processors
        threads = sorted(tracer.thread_states.keys())
        processors = sorted(tracer.processor_assignments.keys())
        
        # Get timeline end
        end_time = min(tracer.current_timestamp, num_cycles)
        
        # Build the timeline
        lines = []
        
        # Header
        header = "Time: "
        for t in range(end_time + 1):
            header += str(t % 10)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Processor timelines
        for processor_id in processors:
            timeline = f"CPU{processor_id}: "
            
            for t in range(end_time + 1):
                thread_id = tracer.get_processor_assignment_at(processor_id, t)
                if thread_id:
                    # Use the first character of the thread ID
                    timeline += thread_id[0] if thread_id else "."
                else:
                    timeline += " "
            
            lines.append(timeline)
        
        lines.append("-" * len(header))
        
        # Thread timelines
        for thread_id in threads:
            timeline = f"T{thread_id[:3]}: "
            
            for t in range(end_time + 1):
                state = tracer.get_thread_state_at(thread_id, t)
                if state:
                    # Use single character codes for states
                    if state == "RUNNING":
                        timeline += "R"
                    elif state == "WAITING":
                        timeline += "W"
                    elif state == "BLOCKED":
                        timeline += "B"
                    elif state == "TERMINATED":
                        timeline += "T"
                    else:
                        timeline += "?"
                else:
                    timeline += " "
            
            lines.append(timeline)
        
        return "\n".join(lines)
    
    @staticmethod
    def create_html_timeline(tracer: ExecutionTracer) -> str:
        """
        Create an HTML timeline visualization.
        
        Args:
            tracer: Execution tracer
            
        Returns:
            HTML timeline string
        """
        # Get all unique threads and processors
        threads = sorted(tracer.thread_states.keys())
        processors = sorted(tracer.processor_assignments.keys())
        
        # Build the HTML
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Execution Timeline</title>",
            "<style>",
            "body { font-family: monospace; }",
            ".timeline { display: flex; flex-direction: column; }",
            ".row { display: flex; height: 20px; margin-bottom: 5px; }",
            ".label { width: 100px; text-align: right; padding-right: 10px; }",
            ".cells { display: flex; }",
            ".cell { width: 20px; height: 20px; text-align: center; line-height: 20px; margin-right: 1px; }",
            ".running { background-color: #4CAF50; }",
            ".waiting { background-color: #FFC107; }",
            ".blocked { background-color: #F44336; }",
            ".terminated { background-color: #9E9E9E; }",
            ".thread-0 { background-color: #2196F3; }",
            ".thread-1 { background-color: #4CAF50; }",
            ".thread-2 { background-color: #FFC107; }",
            ".thread-3 { background-color: #F44336; }",
            ".thread-4 { background-color: #9C27B0; }",
            ".thread-5 { background-color: #00BCD4; }",
            ".thread-none { background-color: #EEEEEE; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Execution Timeline</h1>",
            "<div class='timeline'>",
        ]
        
        # Time header
        header_row = "<div class='row'><div class='label'>Time</div><div class='cells'>"
        for t in range(tracer.current_timestamp + 1):
            header_row += f"<div class='cell'>{t}</div>"
        header_row += "</div></div>"
        html.append(header_row)
        
        # Processor timelines
        for processor_id in processors:
            row = f"<div class='row'><div class='label'>Processor {processor_id}</div><div class='cells'>"
            
            for t in range(tracer.current_timestamp + 1):
                thread_id = tracer.get_processor_assignment_at(processor_id, t)
                
                thread_idx = "none"
                if thread_id:
                    # Get a stable index for the thread
                    try:
                        thread_idx = str(threads.index(thread_id) % 6)
                    except ValueError:
                        thread_idx = "none"
                
                row += f"<div class='cell thread-{thread_idx}'>{thread_id[0] if thread_id else ''}</div>"
            
            row += "</div></div>"
            html.append(row)
        
        # Thread timelines
        for thread_id in threads:
            row = f"<div class='row'><div class='label'>Thread {thread_id}</div><div class='cells'>"
            
            for t in range(tracer.current_timestamp + 1):
                state = tracer.get_thread_state_at(thread_id, t)
                class_name = "cell"
                
                if state:
                    state_lower = state.lower()
                    class_name += f" {state_lower}"
                    label = state[0]
                else:
                    label = ""
                
                row += f"<div class='{class_name}'>{label}</div>"
            
            row += "</div></div>"
            html.append(row)
        
        # Close HTML
        html.extend([
            "</div>",
            "<script>",
            "// Add any JavaScript for interactivity here",
            "</script>",
            "</body>",
            "</html>",
        ])
        
        return "\n".join(html)
    
    @staticmethod
    def export_chrome_tracing(tracer: ExecutionTracer, filename: str) -> None:
        """
        Export trace in Chrome tracing format to a file.
        
        Args:
            tracer: Execution tracer
            filename: Output filename
        """
        trace_json = tracer.export_trace(format="chrome")
        
        with open(filename, "w") as f:
            f.write(trace_json)
    
    @staticmethod
    def export_trace_json(tracer: ExecutionTracer, filename: str) -> None:
        """
        Export trace in JSON format to a file.
        
        Args:
            tracer: Execution tracer
            filename: Output filename
        """
        trace_json = tracer.export_trace(format="json")
        
        with open(filename, "w") as f:
            f.write(trace_json)