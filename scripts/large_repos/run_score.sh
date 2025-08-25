#source .env

# must be run from the unified project's parent directory

if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory_name>"
    echo "Example: $0 text_editor"
    exit 1
fi

directory="$1"

if [ ! -d "large_repos/$directory" ]; then
    echo "Error: Directory '$directory' does not exist"
    exit 1
fi

echo "Running scoring script on refactored repository..."
uv run python -m minicode.score_large_repos --directory "large_repos/$directory/unified" --enable_logprobs > results/large_repos/$directory/score_unified.txt
uv run python -m minicode.score_large_repos --directory "large_repos/$directory" --enable_logprobs  --skip_unified > results/large_repos/$directory/score_original.txt

cp large_repos/$directory/unified/test_output_original.txt results/large_repos/$directory/test_output_original.txt
cp large_repos/$directory/unified/test_output.txt results/large_repos/$directory/test_output.txt
cp large_repos/$directory/unified/report_original.json results/large_repos/$directory/report_original.json
cp large_repos/$directory/unified/report.json results/large_repos/$directory/report.json

echo "Done scoring!"
