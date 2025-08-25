"""PII scanning system for data sources."""

import concurrent.futures
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from privacy_query_interpreter.pii_detection.detector import PIIDetector, PIIMatch


class PIIScanner:
    """
    Scan data sources for PII and generate reports.
    
    This class coordinates PII scanning across various data sources,
    including databases, DataFrames, and CSV files.
    """
    
    def __init__(
        self, 
        detector: Optional[PIIDetector] = None,
        max_workers: int = 4,
        sample_size: int = 1000
    ):
        """
        Initialize the PII scanner.
        
        Args:
            detector: PIIDetector instance (will create default if None)
            max_workers: Maximum number of concurrent workers for scanning
            sample_size: Default sample size for scanning large datasets
        """
        self.detector = detector or PIIDetector()
        self.max_workers = max_workers
        self.sample_size = sample_size
    
    def scan_dataframe(self, df: pd.DataFrame, name: str = "dataframe") -> Dict[str, Any]:
        """
        Scan a pandas DataFrame for PII.
        
        Args:
            df: DataFrame to scan
            name: Name to identify this data source in reports
            
        Returns:
            Scan report with PII findings
        """
        matches = self.detector.detect_in_dataframe(df, self.sample_size)
        
        # Group matches by column
        columns_with_pii = {}
        for match in matches:
            if match.field_name not in columns_with_pii:
                columns_with_pii[match.field_name] = []
            columns_with_pii[match.field_name].append(match.to_dict())
            
        # Build the report
        report = {
            "scan_id": f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "source_type": "dataframe",
            "source_name": name,
            "record_count": len(df),
            "scanned_count": min(len(df), self.sample_size),
            "columns_count": len(df.columns),
            "pii_columns_count": len(columns_with_pii),
            "columns_with_pii": columns_with_pii,
            "summary": {
                "has_pii": len(columns_with_pii) > 0,
                "pii_types_found": list({m.pii_type for m in matches}),
                "pii_categories": list({m.category for m in matches}),
                "highest_sensitivity": max([m.sensitivity_level for m in matches], default=0)
            }
        }
        
        return report
    
    def scan_csv_file(self, file_path: str, **csv_kwargs) -> Dict[str, Any]:
        """
        Scan a CSV file for PII.
        
        Args:
            file_path: Path to the CSV file
            csv_kwargs: Additional arguments to pass to pd.read_csv
            
        Returns:
            Scan report with PII findings
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
            
        try:
            # Read the CSV file
            df = pd.read_csv(file_path, **csv_kwargs)
            
            # Use the filename (without path) as the source name
            source_name = os.path.basename(file_path)
            
            # Scan the dataframe
            report = self.scan_dataframe(df, source_name)
            report["source_type"] = "csv_file"
            report["file_path"] = file_path
            
            return report
        except Exception as e:
            return {
                "scan_id": f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "source_type": "csv_file",
                "source_name": os.path.basename(file_path),
                "file_path": file_path,
                "error": str(e),
                "success": False
            }
    
    def scan_multiple_dataframes(
        self, 
        dataframes: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scan multiple dataframes in parallel.
        
        Args:
            dataframes: Dictionary mapping names to DataFrames
            
        Returns:
            Dictionary mapping names to scan reports
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scanning tasks
            future_to_name = {
                executor.submit(self.scan_dataframe, df, name): name
                for name, df in dataframes.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    results[name] = {
                        "scan_id": f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "timestamp": datetime.now().isoformat(),
                        "source_type": "dataframe",
                        "source_name": name,
                        "error": str(e),
                        "success": False
                    }
        
        return results
    
    def scan_multiple_csv_files(
        self, 
        file_paths: List[str], 
        **csv_kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scan multiple CSV files in parallel.
        
        Args:
            file_paths: List of paths to CSV files
            csv_kwargs: Additional arguments to pass to pd.read_csv
            
        Returns:
            Dictionary mapping file names to scan reports
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scanning tasks
            future_to_path = {
                executor.submit(self.scan_csv_file, path, **csv_kwargs): path
                for path in file_paths
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                name = os.path.basename(path)
                try:
                    results[name] = future.result()
                except Exception as e:
                    results[name] = {
                        "scan_id": f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "timestamp": datetime.now().isoformat(),
                        "source_type": "csv_file",
                        "source_name": name,
                        "file_path": path,
                        "error": str(e),
                        "success": False
                    }
        
        return results
    
    def generate_summary_report(self, scan_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary report from multiple scan results.
        
        Args:
            scan_results: Dictionary mapping names to scan reports
            
        Returns:
            Summary report of all PII findings
        """
        # Initialize summary counters
        total_sources = len(scan_results)
        total_columns = 0
        total_pii_columns = 0
        sources_with_pii = 0
        all_pii_types = set()
        all_pii_categories = set()
        highest_sensitivity = 0
        
        # Sources with highest risk (most PII or highest sensitivity)
        high_risk_sources = []
        
        # Collect PII fields by category
        pii_by_category = {}
        
        # Process each scan result
        for source_name, report in scan_results.items():
            # Skip failed scans
            if "error" in report:
                continue
                
            # Update counters
            total_columns += report.get("columns_count", 0)
            pii_columns = report.get("columns_with_pii", {})
            total_pii_columns += len(pii_columns)
            
            if pii_columns:
                sources_with_pii += 1
                
                # Check if this is a high-risk source
                source_sensitivity = report.get("summary", {}).get("highest_sensitivity", 0)
                if source_sensitivity >= 3 or len(pii_columns) >= 3:
                    high_risk_sources.append({
                        "source_name": source_name,
                        "pii_columns_count": len(pii_columns),
                        "highest_sensitivity": source_sensitivity
                    })
                
                # Update PII types and categories
                all_pii_types.update(report.get("summary", {}).get("pii_types_found", []))
                categories = report.get("summary", {}).get("pii_categories", [])
                all_pii_categories.update(categories)
                
                # Update highest sensitivity
                source_sensitivity = report.get("summary", {}).get("highest_sensitivity", 0)
                highest_sensitivity = max(highest_sensitivity, source_sensitivity)
                
                # Group PII fields by category
                for col_name, matches in pii_columns.items():
                    for match in matches:
                        category = match.get("category")
                        if category not in pii_by_category:
                            pii_by_category[category] = []
                        
                        pii_by_category[category].append({
                            "source": source_name,
                            "field": col_name,
                            "pii_type": match.get("pii_type"),
                            "confidence": match.get("confidence"),
                            "sensitivity": match.get("sensitivity_level")
                        })
        
        # Create the summary report
        summary = {
            "report_id": f"summary_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "total_sources": total_sources,
            "sources_with_pii": sources_with_pii,
            "total_columns": total_columns,
            "total_pii_columns": total_pii_columns,
            "pii_types_found": list(all_pii_types),
            "pii_categories": list(all_pii_categories),
            "highest_sensitivity": highest_sensitivity,
            "high_risk_sources": sorted(high_risk_sources, 
                                       key=lambda x: (x["highest_sensitivity"], x["pii_columns_count"]), 
                                       reverse=True),
            "pii_by_category": pii_by_category,
            "percent_sources_with_pii": round(sources_with_pii / total_sources * 100, 1) if total_sources > 0 else 0,
            "percent_columns_with_pii": round(total_pii_columns / total_columns * 100, 1) if total_columns > 0 else 0
        }
        
        return summary