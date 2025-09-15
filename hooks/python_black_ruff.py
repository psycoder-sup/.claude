#!/usr/bin/env python3
import json
import sys
import subprocess
import os


def main():
    # Read JSON input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)


    # Get the file path from tool input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path")

    if not file_path:
        # No file path, skip
        sys.exit(0)

    # Check if it's a Python file
    if not file_path.endswith(".py"):
        # Not a Python file, skip
        sys.exit(0)

    # Get the working directory
    cwd = input_data.get("cwd", os.getcwd())

    # Run black
    print(f"Running black on {file_path}...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["uv", "run", "black", file_path],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Black error: {result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"Error running black: {e}", file=sys.stderr)

    # Run ruff
    print(f"Running ruff on {file_path}...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--fix", file_path],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Ruff warnings/errors: {result.stdout}", file=sys.stderr)
    except Exception as e:
        print(f"Error running ruff: {e}", file=sys.stderr)

    print(f"Formatted {file_path} with black and ruff", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()