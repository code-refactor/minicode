"""Tests for the PII scanning system."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from privacy_query_interpreter.pii_detection.detector import PIIDetector
from privacy_query_interpreter.pii_detection.scanner import PIIScanner


class TestPIIScanner:
    """Test cases for the PIIScanner class."""
    
    def test_initialization(self):
        """Test scanner initialization with defaults."""
        scanner = PIIScanner()
        assert scanner.detector is not None
        assert scanner.max_workers == 4
        assert scanner.sample_size == 1000
        
        # Test with custom parameters
        detector = PIIDetector()
        custom_scanner = PIIScanner(detector=detector, max_workers=2, sample_size=500)
        assert custom_scanner.detector == detector
        assert custom_scanner.max_workers == 2
        assert custom_scanner.sample_size == 500
    
    def test_scan_dataframe(self, sample_data):
        """Test scanning a DataFrame for PII."""
        scanner = PIIScanner()
        
        # Scan the customers dataframe
        report = scanner.scan_dataframe(sample_data["customers"], "customers_data")
        
        # Check the report structure
        assert "scan_id" in report
        assert "timestamp" in report
        assert report["source_type"] == "dataframe"
        assert report["source_name"] == "customers_data"
        assert report["record_count"] == len(sample_data["customers"])
        assert "columns_count" in report
        assert "pii_columns_count" in report
        assert "columns_with_pii" in report
        assert "summary" in report
        
        # Check the summary content
        summary = report["summary"]
        assert summary["has_pii"] is True
        assert len(summary["pii_types_found"]) > 0
        assert len(summary["pii_categories"]) > 0
        
        # Check that we found expected PII columns
        columns_with_pii = report["columns_with_pii"]
        assert len(columns_with_pii) > 0
        assert any("email" in col.lower() for col in columns_with_pii)
        assert any("phone" in col.lower() for col in columns_with_pii)
        assert any("ssn" in col.lower() for col in columns_with_pii)
        assert any("credit_card" in col.lower() for col in columns_with_pii)
    
    def test_scan_csv_file(self, sample_data, tmp_path):
        """Test scanning a CSV file for PII."""
        # Create a temporary CSV file
        csv_path = os.path.join(tmp_path, "customers.csv")
        sample_data["customers"].to_csv(csv_path, index=False)
        
        scanner = PIIScanner()
        
        # Scan the CSV file
        report = scanner.scan_csv_file(csv_path)
        
        # Check the report structure
        assert "scan_id" in report
        assert "timestamp" in report
        assert report["source_type"] == "csv_file"
        assert report["source_name"] == "customers.csv"
        assert report["file_path"] == csv_path
        assert "columns_count" in report
        assert "pii_columns_count" in report
        assert "columns_with_pii" in report
        assert "summary" in report
        
        # Check the summary content
        summary = report["summary"]
        assert summary["has_pii"] is True
        assert len(summary["pii_types_found"]) > 0
        assert len(summary["pii_categories"]) > 0
    
    def test_scan_nonexistent_csv_file(self):
        """Test scanner behavior with nonexistent files."""
        scanner = PIIScanner()
        
        # Attempt to scan a nonexistent CSV file
        with pytest.raises(FileNotFoundError):
            scanner.scan_csv_file("/path/to/nonexistent/file.csv")
    
    def test_scan_multiple_dataframes(self, sample_data):
        """Test scanning multiple DataFrames in parallel."""
        scanner = PIIScanner()
        
        # Create a dictionary of dataframes
        dataframes = {
            "customers": sample_data["customers"],
            "orders": sample_data["orders"],
            "sensitive_data": sample_data["sensitive_data"]
        }
        
        # Scan all dataframes
        results = scanner.scan_multiple_dataframes(dataframes)
        
        # Check that we got results for all dataframes
        assert len(results) == 3
        assert "customers" in results
        assert "orders" in results
        assert "sensitive_data" in results
        
        # Check that each result has the expected structure
        for name, result in results.items():
            assert "scan_id" in result
            assert "timestamp" in result
            assert result["source_type"] == "dataframe"
            assert result["source_name"] == name
            assert "columns_with_pii" in result
            assert "summary" in result
    
    def test_scan_multiple_csv_files(self, sample_data, tmp_path):
        """Test scanning multiple CSV files in parallel."""
        # Create temporary CSV files
        csv_paths = []
        for name, df in sample_data.items():
            csv_path = os.path.join(tmp_path, f"{name}.csv")
            df.to_csv(csv_path, index=False)
            csv_paths.append(csv_path)
        
        scanner = PIIScanner()
        
        # Scan all CSV files
        results = scanner.scan_multiple_csv_files(csv_paths)
        
        # Check that we got results for all files
        assert len(results) == 3
        
        # Check that each result has the expected structure
        for name, result in results.items():
            assert "scan_id" in result
            assert "timestamp" in result
            assert result["source_type"] == "csv_file"
            assert "file_path" in result
            assert "columns_with_pii" in result
            assert "summary" in result
    
    def test_generate_summary_report(self, sample_data):
        """Test generating a summary report from multiple scan results."""
        scanner = PIIScanner()
        
        # Create individual scan reports
        scan_results = {}
        for name, df in sample_data.items():
            scan_results[name] = scanner.scan_dataframe(df, name)
        
        # Generate a summary report
        summary = scanner.generate_summary_report(scan_results)
        
        # Check the summary structure
        assert "report_id" in summary
        assert "timestamp" in summary
        assert "total_sources" in summary
        assert summary["total_sources"] == 3
        assert "sources_with_pii" in summary
        assert "total_columns" in summary
        assert "total_pii_columns" in summary
        assert "pii_types_found" in summary
        assert "pii_categories" in summary
        assert "high_risk_sources" in summary
        assert "pii_by_category" in summary
        
        # Check the PII categorization
        pii_by_category = summary["pii_by_category"]
        assert len(pii_by_category) > 0
        # Check that we have entries for common categories
        categories = set(pii_by_category.keys())
        assert any("contact" in cat.lower() for cat in categories)
        assert any("financial" in cat.lower() for cat in categories)
    
    def test_error_handling(self):
        """Test error handling in scanning operations."""
        scanner = PIIScanner()
        
        # Create a mock detector that raises an exception
        mock_detector = MagicMock()
        mock_detector.detect_in_dataframe.side_effect = Exception("Detection error")
        scanner.detector = mock_detector
        
        # Create a sample dataframe
        df = pd.DataFrame({
            "name": ["John Doe", "Jane Smith"],
            "email": ["john@example.com", "jane@example.com"]
        })
        
        # Test that the scanner handles the exception gracefully
        with pytest.raises(Exception):
            scanner.scan_dataframe(df, "test_data")
    
    def test_parallel_execution(self, sample_data):
        """Test parallel execution of scanning tasks."""
        # Create a scanner with a single worker to test sequential execution
        sequential_scanner = PIIScanner(max_workers=1)
        
        # Create a scanner with multiple workers for parallel execution
        parallel_scanner = PIIScanner(max_workers=4)
        
        # Create a dictionary of dataframes
        dataframes = {
            "customers": sample_data["customers"],
            "orders": sample_data["orders"],
            "sensitive_data": sample_data["sensitive_data"]
        }
        
        # Time both scanners
        import time
        
        start_time = time.time()
        sequential_results = sequential_scanner.scan_multiple_dataframes(dataframes)
        sequential_time = time.time() - start_time
        
        start_time = time.time()
        parallel_results = parallel_scanner.scan_multiple_dataframes(dataframes)
        parallel_time = time.time() - start_time
        
        # In a real test, we might assert that parallel execution is faster,
        # but for this test we'll just verify both produce the same results
        # since execution times in CI environments can be unpredictable
        assert len(sequential_results) == len(parallel_results)
        assert set(sequential_results.keys()) == set(parallel_results.keys())