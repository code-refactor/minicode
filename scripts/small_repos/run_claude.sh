#!/bin/bash
# must be run from repo base directory
source .env

if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory_name>"
    echo "Example: $0 workflow_orchestration"
    exit 1
fi

directory="$1"
ANTHROPIC_MODEL="claude-3-7-sonnet-20250219"

if [ ! -d "$directory" ]; then
    echo "Error: Directory '$directory' does not exist"
    exit 1
fi

# Run scoring script on initial repository
echo "Running scoring script on initial repository..."
python -m minicode.score_small_repos --directory "$directory" --enable_logprobs

# remember where we started
base_dir="$PWD"

# make a copy to refactor
new_directory="${directory}_refactor_cl" 
cp -r $directory $new_directory
# remove unwanted eval files in copyig
rm -f "$new_directory/LIBRARYBENCH_metrics.json"
rm -f "$new_directory/report.json"
rm -f "$new_directory/test_output.txt"

# Push into the target directory
pushd "$new_directory" >/dev/null
pushd unified >/dev/null

echo "Following the instructions in $base_dir/REFACTOR_INSTRUCTIONS.md..."

echo "Running claude planner"
# Claude plan
claude --dangerously-skip-permissions -p <<EOF
Read the instructions in ../../../prompts/REFACTOR_INSTRUCTIONS.md. Follow the implementation plan and file structure proposed in PLAN.md. IMPORTANT: Create, modify, and reference files ONLY in this current working subdirectory ($new_directory/unified) and nowhere else. Do NOT import from any other subdirectories in $new_directory except for what is here in unified/. Implement ALL code and update ALL test file imports until this whole subfolder is a functional standalone repository. Do not stop to ask for confirmation; keep going until the final implementation passes all tests using pytest tests/.
EOF

# Setup testing environment
uv venv
source .venv/bin/activate
uv pip install -e .

echo "Running claude impl"
# Claude implement
claude --dangerously-skip-permissions -p <<EOF
Read the instructions in ../../../prompts/REFACTOR_INSTRUCTIONS.md. Follow the implementation plan and file structure proposed in PLAN.md. IMPORTANT: Create, modify, and reference files ONLY in this current working subdirectory ($new_directory/unified) and nowhere else. Do NOT import from any other subdirectories in $new_directory except for what is here in unified/. Implement ALL code and update ALL test file imports until this whole subfolder is a functional standalone repository. Do not stop to ask for confirmation; keep going until the final implementation passes all tests using pytest tests/.
EOF

popd >/dev/null
# Now that it's been refactored, remove all original persona subdirs
echo "Cleaning up persona directories..."
for d in */; do
  dir=${d%/}
  if [[ "$dir" != "unified" ]]; then
    echo "  → Removing '$dir'"
    rm -rf "$dir"
  fi
done

pushd unified >/dev/null

# TODO maybe a more elgegant way that discourages this failure mode because its expensive
pytest tests/ --json-report --json-report-file=report.json --continue-on-collection-errors > test_output.txt 2>&1

echo "Running final-check claude impl"
# claude implement
claude --dangerously-skip-permissions -p <<EOF
Read the pytest results in test_output.txt. If they indicate pytest failures, fix them. Stick to the implementation plan and file structure proposed in PLAN.md. IMPORTANT: Create and modify files ONLY in this current working subdirectory ($new_directory/unified) and nowhere else. Implement ALL code and update ALL test file imports until this whole subfolder is a functional standalone repository. Do not stop to ask for confirmation; keep going until the final implementation passes all tests using pytest tests/. If there are no errors, exit.
EOF

pytest tests/ --json-report --json-report-file=report.json --continue-on-collection-errors > test_output.txt 2>&1
deactivate

# Return to original directory
popd >/dev/null
popd >/dev/null

# Run scoring script
echo "Running scoring script on refactored repository..."
uv run python -m minicode.score_small_repos --directory "$new_directory/unified" --enable_logprobs

echo "Done!"
