#!/bin/bash
# Claude development layout: top pane for work, bottom pane for claude

SESSION_NAME="${1:-dev}"
WORKING_DIR="${2:-$(pwd)}"
TOP_PANE_CMD="${3:-claude}"  # Command to run in top pane (default: claude)

# Create new session or attach to existing
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? != 0 ]; then
    # Create session and setup in one command (so tmux knows terminal size)
    tmux new-session -s "$SESSION_NAME" -c "$WORKING_DIR" \; \
        split-window -v -p 70 -c "$WORKING_DIR" \; \
        send-keys Escape "i" "claude" Enter \; \
        select-pane -t 1
else
    tmux attach-session -t "$SESSION_NAME"
fi
