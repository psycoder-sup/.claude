#!/bin/bash
# Claude development layout: top pane for work, bottom pane for claude

NAME="${1:-dev}"
WORKING_DIR="${2:-$(pwd)}"
WORKING_DIR="$(cd "$WORKING_DIR" && pwd)"

# If already inside tmux, create a new window in current session
if [ -n "$TMUX" ]; then
    tmux new-window -n "$NAME" -c "$WORKING_DIR" \; \
        split-window -v -p 70 -c "$WORKING_DIR" \; \
        send-keys claude Enter \; \
        select-pane -t 1
    exit 0
fi

# Outside tmux: create new session or attach to existing
tmux has-session -t "=$NAME" 2>/dev/null

if [ $? != 0 ]; then
    # Create session and setup in one command (so tmux knows terminal size)
    tmux new-session -s "$NAME" -n "main" -c "$WORKING_DIR" \; \
        split-window -v -p 70 -c "$WORKING_DIR" \; \
        send-keys claude Enter \; \
        select-pane -t 1
else
    tmux attach-session -t "$NAME"
fi
