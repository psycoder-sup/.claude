#!/bin/bash
# Claude development layout: top pane for work, bottom pane for claude

SESSION_NAME="${1:-dev}"
WORKING_DIR="${2:-$(pwd)}"
TOP_PANE_CMD="${3:-claude}"  # Command to run in top pane (default: claude)

# Create new session or attach to existing
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? != 0 ]; then
    # Create new session
    tmux new-session -d -s "$SESSION_NAME" -c "$WORKING_DIR"

    # Split horizontally (top/bottom) with 30:70 ratio
    tmux split-window -v -p 70 -c "$WORKING_DIR"

    # Wait for shells to initialize
    sleep 0.5

    # Run claude in bottom pane (pane 2) - Escape+i for vim mode shells
    tmux send-keys -t "$SESSION_NAME:1.2" Escape "i" "claude" Enter

    # # Run command in top pane if specified - Escape+i for vim mode shells
    # if [ -n "$TOP_PANE_CMD" ]; then
    #     tmux send-keys -t "$SESSION_NAME:1.1" Escape "i" "$TOP_PANE_CMD" Enter
    # fi

    # Focus on top pane (pane 1)
    tmux select-pane -t "$SESSION_NAME:1.1"
fi

# Attach to session
tmux attach-session -t "$SESSION_NAME"
