#!/usr/bin/env python3
"""
Colorful status line for Claude Code with emojis
Shows: time | model | project | branch
"""

import json
import sys
import subprocess
import os
from datetime import datetime


def get_git_branch(cwd):
    """Get the current git branch for the given directory."""
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout.strip() if result.returncode == 0 else "no-git"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "no-git"


def get_project_name(project_dir):
    """Extract project name from project directory path."""
    return os.path.basename(project_dir) if project_dir else "unknown"


def colorize(text, color_code):
    """Apply ANSI color codes to text for terminal display."""
    return f"\033[{color_code}m{text}\033[0m"


def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Extract data from input
        model_name = input_data.get('model', {}).get('display_name', 'Unknown Model')
        cwd = input_data.get('workspace', {}).get('current_dir', os.getcwd())
        project_dir = input_data.get('workspace', {}).get('project_dir', cwd)
        
        # Get current time
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Get git branch
        git_branch = get_git_branch(cwd)
        
        # Get project name
        project_name = get_project_name(project_dir)
        
        # Create colorful status line components with emojis
        time_part = f"🕐 {colorize(current_time, '36')}"  # Cyan
        model_part = f"🤖 {colorize(model_name, '35')}"    # Magenta  
        project_part = f"📁 {colorize(project_name, '33')}" # Yellow
        branch_part = f"🌿 {colorize(git_branch, '32')}"    # Green
        
        # Combine with separators
        separator = colorize(" | ", "2")  # Dimmed
        status_line = separator.join([time_part, model_part, project_part, branch_part])
        
        print(status_line)
        
    except (json.JSONDecodeError, KeyError) as e:
        # Fallback in case of input issues
        error_msg = colorize(f"❌ Status error: {str(e)}", "31")  # Red
        print(error_msg)
    except Exception as e:
        # General error fallback
        error_msg = colorize(f"⚠️  Status unavailable: {str(e)}", "31")  # Red
        print(error_msg)


if __name__ == "__main__":
    main()