"""Main entry point for the Database Storage Optimization Analyzer."""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import json

from .interfaces.api import StorageOptimizerAPI
from .utils.types import DatabaseEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Database Storage Optimization Analyzer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Main arguments
    parser.add_argument(
        "path", 
        nargs="?",
        help="Path to analyze (directory containing database files)",
        type=str,
        default="."
    )
    
    # Analysis type
    parser.add_argument(
        "--analysis-type", "-t",
        help="Type of analysis to perform",
        choices=["all", "files", "logs", "indexes", "tablespaces", "backups"],
        default="all"
    )
    
    # Export options
    parser.add_argument(
        "--export-format", "-f",
        help="Export format for analysis results",
        choices=["json", "csv", "html", "none"],
        default="json"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory for output files",
        type=str,
        default="./output"
    )
    
    parser.add_argument(
        "--output-filename",
        help="Filename for export (without extension)",
        type=str,
        default="analysis_result"
    )
    
    # Search options
    parser.add_argument(
        "--recursive", "-r",
        help="Search subdirectories recursively",
        action="store_true",
        default=True
    )
    
    parser.add_argument(
        "--max-depth",
        help="Maximum directory depth to search",
        type=int,
        default=None
    )
    
    parser.add_argument(
        "--follow-symlinks",
        help="Follow symbolic links during search",
        action="store_true",
        default=False
    )
    
    # Database engine filter
    parser.add_argument(
        "--engine",
        help="Filter analysis to specific database engine",
        choices=["mysql", "postgresql", "mongodb", "oracle", "mssql", "all"],
        default="all"
    )
    
    # Notification options
    parser.add_argument(
        "--notify",
        help="Send notifications for critical findings",
        action="store_true",
        default=False
    )
    
    parser.add_argument(
        "--email",
        help="Email address for notifications",
        type=str,
        default=None
    )
    
    # Debugging and verbose output
    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose output",
        action="store_true",
        default=False
    )
    
    parser.add_argument(
        "--debug",
        help="Enable debug logging",
        action="store_true",
        default=False
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the command line interface."""
    args = parse_arguments()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        os.makedirs(output_dir)
    
    # Initialize API
    api = StorageOptimizerAPI(output_dir=output_dir)
    
    # Prepare export options
    export_format = None if args.export_format == "none" else args.export_format
    export_filename = f"{args.output_filename}.{args.export_format}" if export_format else None
    
    # Prepare notification options
    notify = args.notify and args.email is not None
    
    # Validate path
    path = Path(args.path)
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        return 1
    
    try:
        # Perform requested analysis
        if args.analysis_type == "all" or args.analysis_type == "files":
            logger.info(f"Analyzing database files in {path}")
            file_result = api.analyze_database_files(
                root_path=path,
                recursive=args.recursive,
                max_depth=args.max_depth,
                follow_symlinks=args.follow_symlinks,
                export_format=export_format,
                export_filename=f"file_analysis_{export_filename}" if export_filename else None,
                notify_on_critical=notify,
                notification_email=args.email,
            )
            
            # Print summary
            if args.verbose:
                print("\nFile Analysis Summary:")
                print(f"  Total files scanned: {file_result.get('total_files_scanned', 0)}")
                print(f"  Total size: {file_result.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
                print(f"  Files by engine: {file_result.get('files_by_engine', {})}")
                print(f"  Recommendations: {len(file_result.get('recommendations', []))}")
                
        # If analysis_type is "all", perform comprehensive analysis
        if args.analysis_type == "all":
            logger.info(f"Performing comprehensive analysis of {path}")
            result = api.comprehensive_analysis(
                root_path=path,
                recursive=args.recursive,
                export_format=export_format,
                export_filename=export_filename,
                notify_on_critical=notify,
                notification_email=args.email,
            )
            
            # Print summary
            if args.verbose:
                print("\nComprehensive Analysis Summary:")
                print(f"  Total files: {result.get('file_analysis', {}).get('total_files_scanned', 0)}")
                print(f"  Total recommendations: {len(result.get('all_recommendations', []))}")
                
                # Print critical recommendations
                critical_recs = [r for r in result.get('all_recommendations', []) 
                              if r.get('priority') in ['critical', 'high']]
                if critical_recs:
                    print("\nCritical Recommendations:")
                    for i, rec in enumerate(critical_recs[:5]):  # Show top 5
                        print(f"  {i+1}. [{rec.get('priority')}] {rec.get('title')}")
                    
                    if len(critical_recs) > 5:
                        print(f"  ... and {len(critical_recs) - 5} more critical recommendations")
                        
        # Specific log analysis if requested
        if args.analysis_type == "logs":
            logger.info(f"Analyzing transaction logs in {path}")
            
            # First find log files
            file_result = api.analyze_database_files(
                root_path=path,
                recursive=args.recursive,
                max_depth=args.max_depth,
                follow_symlinks=args.follow_symlinks,
            )
            
            log_files = [f for f in file_result.get("detected_files", []) 
                      if f.get("category") == "log"]
            
            if not log_files:
                logger.warning("No log files found in the specified path")
                return 0
                
            log_result = api.analyze_transaction_logs(
                log_files=log_files,
                export_format=export_format,
                export_filename=f"log_analysis_{export_filename}" if export_filename else None,
                notify_on_critical=notify,
                notification_email=args.email,
            )
            
            # Print summary
            if args.verbose:
                print("\nLog Analysis Summary:")
                print(f"  Total log files: {len(log_files)}")
                print(f"  Total log size: {log_result.get('total_log_size_bytes', 0) / (1024*1024):.2f} MB")
                print(f"  Growth rate: {log_result.get('growth_rate_bytes_per_day', 0) / (1024*1024):.2f} MB/day")
                print(f"  Growth pattern: {log_result.get('dominant_growth_pattern', 'unknown')}")
                
        # Specific backup analysis if requested
        if args.analysis_type == "backups":
            logger.info(f"Analyzing backup files in {path}")
            
            # First find backup files
            file_result = api.analyze_database_files(
                root_path=path,
                recursive=args.recursive,
                max_depth=args.max_depth,
                follow_symlinks=args.follow_symlinks,
            )
            
            backup_files = [f for f in file_result.get("detected_files", []) 
                         if f.get("category") == "backup"]
            
            if not backup_files:
                logger.warning("No backup files found in the specified path")
                return 0
                
            backup_result = api.analyze_backup_compression(
                backups=backup_files,
                export_format=export_format,
                export_filename=f"backup_analysis_{export_filename}" if export_filename else None,
                notify_on_critical=notify,
                notification_email=args.email,
            )
            
            # Print summary
            if args.verbose:
                print("\nBackup Analysis Summary:")
                print(f"  Total backup files: {backup_result.get('total_backups', 0)}")
                print(f"  Total backup size: {backup_result.get('total_backup_size_bytes', 0) / (1024*1024):.2f} MB")
                print(f"  Compression ratio: {backup_result.get('overall_compression_ratio', 0):.2f}x")
                print(f"  Space savings: {backup_result.get('overall_space_savings_bytes', 0) / (1024*1024):.2f} MB")
        
        logger.info("Analysis completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=args.debug)
        return 1


if __name__ == "__main__":
    sys.exit(main())