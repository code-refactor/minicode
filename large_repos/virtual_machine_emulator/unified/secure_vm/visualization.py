"""
Visualization utilities for the secure VM.

This module provides visualization capabilities for control flow integrity,
memory access patterns, and attack analysis.
"""

from __future__ import annotations
import json
import time
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from secure_vm.cpu import ControlFlowRecord
from secure_vm.emulator import ExecutionResult, VirtualMachine


class ControlFlowVisualizer:
    """Visualizes control flow integrity and attack effects."""
    
    def __init__(self, format_type: str = "text"):
        self.format_type = format_type
    
    def visualize_control_flow(
        self,
        control_flow_records: List[ControlFlowRecord],
        highlight_illegitimate: bool = True,
    ) -> str:
        """
        Create a text-based visualization of control flow.
        
        This method provides a simple text-based visualization suitable for
        console output.
        """
        visualization = []
        
        visualization.append("Control Flow Trace:")
        visualization.append("===================")
        
        for i, record in enumerate(control_flow_records):
            line = f"{i+1:3d}. 0x{record.from_address:08x} -> 0x{record.to_address:08x}"
            line += f" [{record.event_type}] via {record.instruction}"
            
            if highlight_illegitimate and not record.legitimate:
                line += " ** HIJACKED **"
            
            visualization.append(line)
        
        if not control_flow_records:
            visualization.append("No control flow events recorded.")
        
        return "\n".join(visualization)
    
    def visualize_control_flow_graph(
        self,
        execution_result: ExecutionResult,
    ) -> Dict[str, Any]:
        """
        Create a graph representation of control flow.
        
        This method generates a graph structure that can be used for
        visualization in various formats. The result is returned as a
        dictionary with nodes and edges.
        """
        # Extract control flow events
        events = execution_result.control_flow_events
        
        # Build node and edge sets
        nodes = set()
        node_info = {}
        edges = []
        
        for event in events:
            from_addr = event["from_address"]
            to_addr = event["to_address"]
            
            nodes.add(from_addr)
            nodes.add(to_addr)
            
            # Track node metadata
            if from_addr not in node_info:
                node_info[from_addr] = {"used_in_events": 0, "hijack_source": False}
            if to_addr not in node_info:
                node_info[to_addr] = {"used_in_events": 0, "hijack_target": False}
            
            node_info[from_addr]["used_in_events"] += 1
            node_info[to_addr]["used_in_events"] += 1
            
            # Mark hijacked flow nodes
            if not event["legitimate"]:
                node_info[from_addr]["hijack_source"] = True
                node_info[to_addr]["hijack_target"] = True
            
            # Add edge
            edge = {
                "source": from_addr,
                "target": to_addr,
                "type": event["event_type"],
                "legitimate": event["legitimate"],
                "instruction": event["instruction"],
            }
            edges.append(edge)
        
        # Format node list with metadata
        node_list = []
        for addr in sorted(nodes):
            info = node_info[addr]
            node = {
                "address": addr,
                "frequency": info["used_in_events"],
                "hijack_source": info["hijack_source"],
                "hijack_target": info["hijack_target"],
            }
            node_list.append(node)
        
        return {
            "nodes": node_list,
            "edges": edges,
            "event_count": len(events),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "legitimate_flow": all(edge["legitimate"] for edge in edges),
        }
    
    def compare_control_flows(
        self,
        normal_flow: Dict[str, Any],
        compromised_flow: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare normal and compromised control flows to highlight differences.
        
        This method helps identify exactly how an attack modified the control flow
        by comparing the normal execution path with the compromised one.
        """
        # Extract nodes and edges
        normal_nodes = {node["address"] for node in normal_flow["nodes"]}
        normal_edges = {(edge["source"], edge["target"]) for edge in normal_flow["edges"]}
        
        compromised_nodes = {node["address"] for node in compromised_flow["nodes"]}
        compromised_edges = {(edge["source"], edge["target"]) for edge in compromised_flow["edges"]}
        
        # Find differences
        new_nodes = compromised_nodes - normal_nodes
        new_edges = compromised_edges - normal_edges
        missing_nodes = normal_nodes - compromised_nodes
        missing_edges = normal_edges - compromised_edges
        
        # Find hijacked edges in compromised flow
        hijacked_edges = []
        for edge in compromised_flow["edges"]:
            if not edge["legitimate"]:
                hijacked_edges.append((edge["source"], edge["target"]))
        
        return {
            "new_nodes": sorted(new_nodes),
            "new_edges": sorted(new_edges),
            "missing_nodes": sorted(missing_nodes),
            "missing_edges": sorted(missing_edges),
            "hijacked_edges": sorted(hijacked_edges),
            "normal_flow_events": normal_flow["event_count"],
            "compromised_flow_events": compromised_flow["event_count"],
            "has_differences": bool(new_nodes or new_edges or missing_nodes or missing_edges),
            "has_hijacked_flow": bool(hijacked_edges),
        }


class MemoryAccessVisualizer:
    """Visualizes memory access patterns."""
    
    def __init__(self, vm: VirtualMachine):
        self.vm = vm
    
    def visualize_memory_access_pattern(self, format_type: str = "text") -> Union[str, Dict[str, Any]]:
        """
        Create a visualization of memory access patterns.
        
        This method analyzes the forensic logs to identify patterns in memory accesses,
        which can help identify abnormal behavior or attacks.
        """
        # Get logs with memory access events
        logs = self.vm.forensic_log.logs
        
        # Extract memory access events
        memory_events = []
        for log in logs:
            if log["event_type"] == "memory_access":
                memory_events.append(log["data"])
        
        # Group by operation type (read, write, execute)
        access_by_type = {
            "read": [],
            "write": [],
            "execute": [],
        }
        
        for event in memory_events:
            access_type = event["access_type"]
            if access_type in access_by_type:
                access_by_type[access_type].append(event)
        
        # Count accesses for each segment
        segment_access_counts = {}
        for segment in self.vm.memory.segments:
            segment_access_counts[segment.name] = {
                "read": 0,
                "write": 0,
                "execute": 0,
                "total": 0,
            }
        
        # Process all events
        for access_type, events in access_by_type.items():
            for event in events:
                address = event["address"]
                segment = self.vm.memory.find_segment(address)
                if segment:
                    segment_access_counts[segment.name][access_type] += 1
                    segment_access_counts[segment.name]["total"] += 1
        
        # Generate the visualization based on format type
        if format_type == "text":
            return self._generate_text_visualization(access_by_type, segment_access_counts)
        else:
            return {
                "access_by_type": {k: len(v) for k, v in access_by_type.items()},
                "segment_access_counts": segment_access_counts,
                "total_events": len(memory_events),
            }
    
    def _generate_text_visualization(
        self,
        access_by_type: Dict[str, List[Dict[str, Any]]],
        segment_access_counts: Dict[str, Dict[str, int]],
    ) -> str:
        """Generate a text-based visualization of memory access patterns."""
        lines = []
        
        lines.append("Memory Access Pattern Analysis")
        lines.append("=============================")
        lines.append("")
        
        # Summary by operation type
        lines.append("Access by Operation Type:")
        lines.append(f"Read operations:  {len(access_by_type['read']):10d}")
        lines.append(f"Write operations: {len(access_by_type['write']):10d}")
        lines.append(f"Execute operations: {len(access_by_type['execute']):8d}")
        lines.append(f"Total operations: {sum(len(v) for v in access_by_type.values()):10d}")
        lines.append("")
        
        # Summary by memory segment
        lines.append("Access by Memory Segment:")
        for segment_name, counts in segment_access_counts.items():
            lines.append(f"Segment: {segment_name}")
            lines.append(f"  Read:    {counts['read']:10d}")
            lines.append(f"  Write:   {counts['write']:10d}")
            lines.append(f"  Execute: {counts['execute']:10d}")
            lines.append(f"  Total:   {counts['total']:10d}")
        
        return "\n".join(lines)
    
    def detect_abnormal_patterns(self) -> Dict[str, Any]:
        """
        Detect potentially abnormal memory access patterns.
        
        This method identifies suspicious patterns like:
        - Execution from normally non-executable regions
        - Unusual read/write patterns in the stack
        - Access to unmapped memory
        """
        logs = self.vm.forensic_log.logs
        abnormal_patterns = []
        
        # Look for specific suspicious patterns
        for log in logs:
            if log["event_type"] == "memory_access":
                data = log["data"]
                address = data["address"]
                access_type = data["access_type"]
                segment = self.vm.memory.find_segment(address)
                
                # Check for execution from non-executable segments
                if (access_type == "execute" and segment and 
                        not segment.check_permission(address, segment.permission.__class__.EXECUTE)):
                    abnormal_patterns.append({
                        "type": "execute_from_non_executable",
                        "address": address,
                        "segment": segment.name,
                        "timestamp": log["timestamp"],
                    })
                
                # Check for access to unmapped memory
                if segment is None:
                    abnormal_patterns.append({
                        "type": "access_unmapped_memory",
                        "address": address,
                        "access_type": access_type,
                        "timestamp": log["timestamp"],
                    })
                
                # Check for writes to the code segment
                if (access_type == "write" and segment and 
                        segment.name == "code"):
                    abnormal_patterns.append({
                        "type": "write_to_code",
                        "address": address,
                        "timestamp": log["timestamp"],
                    })
            
            # Also look for protection events
            elif log["event_type"] == "protection_violation":
                abnormal_patterns.append({
                    "type": "protection_violation",
                    "details": log["data"],
                    "timestamp": log["timestamp"],
                })
        
        return {
            "abnormal_patterns": abnormal_patterns,
            "count": len(abnormal_patterns),
            "has_abnormal_patterns": len(abnormal_patterns) > 0,
        }


class ForensicAnalyzer:
    """Analyzes forensic data to detect and explain attacks."""
    
    def __init__(self, vm: VirtualMachine):
        self.vm = vm
    
    def analyze_execution(self, execution_result: ExecutionResult) -> Dict[str, Any]:
        """
        Perform forensic analysis on an execution result.
        
        This method examines the execution result to identify signs of attacks,
        exploitation attempts, and security violations.
        """
        analysis = {
            "suspicious_events": [],
            "attack_indicators": {},
            "execution_summary": execution_result.get_summary(),
            "exploitation_detected": False,
        }
        
        # Look for illegitimate control flow events
        hijacked_flows = []
        for event in execution_result.control_flow_events:
            if not event["legitimate"]:
                hijacked_flows.append(event)
        
        if hijacked_flows:
            analysis["suspicious_events"].append({
                "type": "control_flow_hijacking",
                "events": hijacked_flows,
                "count": len(hijacked_flows),
            })
            analysis["exploitation_detected"] = True
            analysis["attack_indicators"]["control_flow_hijacking"] = True
        
        # Look for protection events
        if execution_result.protection_events:
            analysis["suspicious_events"].append({
                "type": "protection_violations",
                "events": execution_result.protection_events,
                "count": len(execution_result.protection_events),
            })
            analysis["attack_indicators"]["protection_violations"] = True
        
        # Memory corruption indicators from forensic logs
        canary_violations = []
        for log in self.vm.forensic_log.logs:
            if log["event_type"] == "system" and log["data"].get("system_event") == "canary_violation":
                canary_violations.append(log["data"])
        
        if canary_violations:
            analysis["suspicious_events"].append({
                "type": "stack_canary_violations",
                "events": canary_violations,
                "count": len(canary_violations),
            })
            analysis["attack_indicators"]["stack_corruption"] = True
            analysis["exploitation_detected"] = True
        
        # Check for DEP violations
        dep_violations = []
        for event in execution_result.protection_events:
            if event["access_type"] == "execute" and event["required_permission"] == "EXECUTE":
                dep_violations.append(event)
        
        if dep_violations:
            analysis["suspicious_events"].append({
                "type": "dep_violations",
                "events": dep_violations,
                "count": len(dep_violations),
            })
            analysis["attack_indicators"]["dep_bypass_attempt"] = True
        
        # Check for privilege escalation
        privilege_changes = []
        for event in execution_result.control_flow_events:
            if event["event_type"] == "privilege-change":
                privilege_changes.append(event)
        
        if privilege_changes:
            # This isn't necessarily malicious, but we record it
            analysis["suspicious_events"].append({
                "type": "privilege_changes",
                "events": privilege_changes,
                "count": len(privilege_changes),
            })
            
            # Check if any were unexpected
            unexpected_changes = []
            for event in privilege_changes:
                if not event["legitimate"]:
                    unexpected_changes.append(event)
            
            if unexpected_changes:
                analysis["attack_indicators"]["privilege_escalation"] = True
                analysis["exploitation_detected"] = True
        
        # Determine attack type if exploitation was detected
        if analysis["exploitation_detected"]:
            attack_type = self._identify_attack_type(analysis)
            analysis["identified_attack_type"] = attack_type
        
        return analysis
    
    def _identify_attack_type(self, analysis: Dict[str, Any]) -> str:
        """Identify the most likely attack type based on forensic evidence."""
        indicators = analysis["attack_indicators"]
        
        if "dep_bypass_attempt" in indicators:
            if "control_flow_hijacking" in indicators:
                return "return_oriented_programming"
            else:
                return "code_injection"
        
        if "stack_corruption" in indicators and "control_flow_hijacking" in indicators:
            return "buffer_overflow"
        
        if "privilege_escalation" in indicators:
            return "privilege_escalation"
        
        # Default if we can't specifically identify
        return "unknown_exploitation"
    
    def compare_protection_strategies(
        self,
        comparison_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze results from comparing different protection strategies.
        
        This method examines the results of running the same attack against
        different protection configurations to understand their effectiveness.
        """
        analysis = {
            "strategies": [],
            "most_effective": None,
            "least_effective": None,
            "summary": "",
        }
        
        # Process each strategy result
        for result in comparison_results:
            protection = result["protection"]
            effectiveness = 100 - (100 if result["attack_successful"] else 0)
            
            strategy_analysis = {
                "protection": protection,
                "effectiveness": effectiveness,
                "attack_successful": result["attack_successful"],
                "detection_events": result["protection_events"],
                "execution_result": result["execution_result"],
            }
            
            analysis["strategies"].append(strategy_analysis)
        
        # Sort by effectiveness
        analysis["strategies"].sort(key=lambda x: x["effectiveness"], reverse=True)
        
        # Identify most and least effective
        if analysis["strategies"]:
            analysis["most_effective"] = analysis["strategies"][0]
            analysis["least_effective"] = analysis["strategies"][-1]
        
        # Generate summary
        if analysis["strategies"]:
            most_effective = analysis["most_effective"]["protection"]
            most_effective_desc = f"Level: {most_effective['protection_level']}, "
            most_effective_desc += f"DEP: {most_effective['dep_enabled']}, "
            most_effective_desc += f"ASLR: {most_effective['aslr_enabled']}, "
            most_effective_desc += f"Canaries: {most_effective['stack_canaries']}"
            
            least_effective = analysis["least_effective"]["protection"]
            least_effective_desc = f"Level: {least_effective['protection_level']}, "
            least_effective_desc += f"DEP: {least_effective['dep_enabled']}, "
            least_effective_desc += f"ASLR: {least_effective['aslr_enabled']}, "
            least_effective_desc += f"Canaries: {least_effective['stack_canaries']}"
            
            summary = f"Most effective protection: {most_effective_desc} ({analysis['most_effective']['effectiveness']}%)\n"
            summary += f"Least effective protection: {least_effective_desc} ({analysis['least_effective']['effectiveness']}%)"
            
            analysis["summary"] = summary
        
        return analysis