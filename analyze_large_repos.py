#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

def extract_log_prob_from_score_file(score_file_path):
    """Extract the full repo log probability from a score file."""
    if not score_file_path.exists():
        return None
    
    with open(score_file_path, 'r') as f:
        content = f.read()
    
    # Look for "Full Repo Log Probability: <number>"
    match = re.search(r'Full Repo Log Probability:\s*([-\d.]+)', content)
    if match:
        return float(match.group(1))
    return None

def analyze_repo(repo_path):
    """Analyze a single repository's results."""
    report_path = repo_path / "report.json"
    report_original_path = repo_path / "report_original.json"
    score_unified_path = repo_path / "score_unified.txt"
    score_original_path = repo_path / "score_original.txt"
    
    if not report_path.exists() or not report_original_path.exists():
        return None
    
    with open(report_path) as f:
        report_unified = json.load(f)
    
    with open(report_original_path) as f:
        report_original = json.load(f)
    
    # Extract pass rates from test summaries
    unified_summary = report_unified.get("summary", {})
    original_summary = report_original.get("summary", {})
    
    unified_passed = unified_summary.get("passed", 0)
    unified_total = unified_summary.get("total", 1)
    original_passed = original_summary.get("passed", 0)
    original_total = original_summary.get("total", 1)
    
    unified_pass_rate = unified_passed / unified_total if unified_total > 0 else 0
    original_pass_rate = original_passed / original_total if original_total > 0 else 0
    
    # Extract full repo log probabilities from score files
    unified_log_prob = extract_log_prob_from_score_file(score_unified_path)
    original_log_prob = extract_log_prob_from_score_file(score_original_path)
    
    # Calculate log prob ratio if both exist
    log_prob_ratio = None
    if unified_log_prob is not None and original_log_prob is not None and original_log_prob != 0:
        log_prob_ratio = unified_log_prob / original_log_prob
    
    return {
        "unified_pass_rate": unified_pass_rate,
        "original_pass_rate": original_pass_rate,
        "unified_log_prob": unified_log_prob,
        "original_log_prob": original_log_prob,
        "log_prob_ratio": log_prob_ratio,
        "unified_passed": unified_passed,
        "unified_total": unified_total,
        "original_passed": original_passed,
        "original_total": original_total
    }

def main():
    results_dir = Path("results/large_repos")
    
    if not results_dir.exists():
        print(f"Directory {results_dir} does not exist")
        return
    
    repos = sorted([d for d in results_dir.iterdir() if d.is_dir()])
    
    print(f"{'Repository':<35} {'Pass Rate (Unified)':<25} {'Pass Rate (Original)':<25} {'Log Prob Ratio':<15}")
    print("=" * 100)
    
    for repo_dir in repos:
        repo_name = repo_dir.name
        result = analyze_repo(repo_dir)
        
        if result:
            unified_pass = f"{result['unified_pass_rate']:.1%} ({result['unified_passed']}/{result['unified_total']})"
            original_pass = f"{result['original_pass_rate']:.1%} ({result['original_passed']}/{result['original_total']})"
            ratio = f"{result['log_prob_ratio']:.4f}" if result['log_prob_ratio'] is not None else "N/A"
            
            print(f"{repo_name:<35} {unified_pass:<25} {original_pass:<25} {ratio:<15}")
        else:
            print(f"{repo_name:<35} {'Missing data':<25} {'Missing data':<25} {'N/A':<15}")
    
    # Calculate and print summary statistics
    print("\n" + "=" * 100)
    print("Summary Statistics")
    print("=" * 100)
    
    valid_results = [analyze_repo(repo_dir) for repo_dir in repos]
    valid_results = [r for r in valid_results if r is not None]
    
    if valid_results:
        # Average pass rates
        avg_unified_pass = sum(r['unified_pass_rate'] for r in valid_results if r['unified_pass_rate'] is not None) / len(valid_results)
        avg_original_pass = sum(r['original_pass_rate'] for r in valid_results if r['original_pass_rate'] is not None) / len(valid_results)
        
        # Average log prob ratio
        ratios = [r['log_prob_ratio'] for r in valid_results if r['log_prob_ratio'] is not None]
        avg_ratio = sum(ratios) / len(ratios) if ratios else None
        
        print(f"Average Pass Rate (Unified):  {avg_unified_pass:.2%}")
        print(f"Average Pass Rate (Original): {avg_original_pass:.2%}")
        if avg_ratio:
            print(f"Average Log Prob Ratio:       {avg_ratio:.4f}")
            print(f"Number of repos with ratio:   {len(ratios)}/{len(valid_results)}")

if __name__ == "__main__":
    main()