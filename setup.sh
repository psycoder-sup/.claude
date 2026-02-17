#!/usr/bin/env bash
# =============================================================================
# Dotfiles Symlink Setup Script
# Creates symlinks from ~/.claude config files to their expected locations.
# Safe to run multiple times — existing symlinks are replaced, regular files
# are backed up before overwriting.
# =============================================================================

set -euo pipefail

DOTFILES_DIR="$HOME/.claude"
BACKUP_DIR="$DOTFILES_DIR/backup/$(date +%Y%m%d_%H%M%S)"
DRY_RUN=false

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { printf "\033[34m[INFO]\033[0m  %s\n" "$1"; }
ok()    { printf "\033[32m[OK]\033[0m    %s\n" "$1"; }
warn()  { printf "\033[33m[WARN]\033[0m  %s\n" "$1"; }
err()   { printf "\033[31m[ERR]\033[0m   %s\n" "$1"; }

backup_if_exists() {
    local target="$1"
    if [[ -e "$target" && ! -L "$target" ]]; then
        mkdir -p "$BACKUP_DIR"
        mv "$target" "$BACKUP_DIR/"
        warn "Backed up existing $target -> $BACKUP_DIR/$(basename "$target")"
    fi
}

create_symlink() {
    local source="$1"
    local target="$2"

    if [[ ! -e "$source" ]]; then
        err "Source does not exist: $source"
        return 1
    fi

    if $DRY_RUN; then
        info "[dry-run] $target -> $source"
        return 0
    fi

    mkdir -p "$(dirname "$target")"

    if [[ -L "$target" ]]; then
        rm "$target"
    else
        backup_if_exists "$target"
    fi

    ln -s "$source" "$target"
    ok "$target -> $source"
}

# ---------------------------------------------------------------------------
# Symlink definitions
# ---------------------------------------------------------------------------

setup_symlinks() {
    info "Setting up symlinks..."
    echo

    # --- Tmux ---
    info "tmux"
    create_symlink "$DOTFILES_DIR/tmux/tmux.conf"             "$HOME/.tmux.conf"
    create_symlink "$DOTFILES_DIR/tmux/.tmux-sessionizer"      "$HOME/.tmux-sessionizer"
    create_symlink "$DOTFILES_DIR/tmux/tmux-sessionizer.conf"  "$HOME/.config/tmux-sessionizer/tmux-sessionizer.conf"
    echo

    # --- Scripts -> ~/.local/bin ---
    info "scripts (~/.local/bin)"
    create_symlink "$DOTFILES_DIR/tmux/tmux-sessionizer"           "$HOME/.local/bin/tmux-sessionizer"
    create_symlink "$DOTFILES_DIR/tmux/tmux-claude.sh"             "$HOME/.local/bin/tmux-claude.sh"
    create_symlink "$DOTFILES_DIR/ghostty/ghostty-worktree-tab.sh" "$HOME/.local/bin/ghostty-worktree-tab.sh"
    echo

    # --- Ghostty ---
    info "ghostty"
    create_symlink "$DOTFILES_DIR/ghostty/ghostty.config"      "$HOME/.config/ghostty/config"
    echo

    # --- Yazi ---
    info "yazi"
    create_symlink "$DOTFILES_DIR/yazi"                        "$HOME/.config/yazi"
    echo
}

# ---------------------------------------------------------------------------
# Verify PATH includes ~/.local/bin
# ---------------------------------------------------------------------------

check_path() {
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warn "\$HOME/.local/bin is not in your PATH."
        warn "Add to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run) DRY_RUN=true; shift ;;
            --help|-h)
                echo "Usage: $(basename "$0") [--dry-run]"
                exit 0 ;;
            *) err "Unknown option: $1"; exit 1 ;;
        esac
    done

    echo "========================================"
    echo "  Dotfiles Symlink Setup"
    echo "========================================"
    echo

    if $DRY_RUN; then
        warn "Dry-run mode — no changes will be made."
        echo
    fi

    setup_symlinks
    check_path

    echo "========================================"
    echo "  Done!"
    echo "========================================"
}

main "$@"
