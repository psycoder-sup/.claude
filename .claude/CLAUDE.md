# Project Instructions

## Configuration Files

- **tmux config**: The tmux configuration file is located at `tmux/tmux.conf` in this directory. `~/.tmux.conf` is a symbolic link to this file.
- **yazi config**: The yazi file manager configuration is in the `yazi/` directory. `~/.config/yazi` is a symbolic link to this directory. Key files: `yazi.toml` (main config), `keymap.toml` (keybindings), `theme.toml` (theme), `init.lua` (init script), `package.toml` (plugins).
- **tmux pane layout**: Both `scripts/gw.sh` and `tmux/.tmux-sessionizer` (hydrate config, symlinked to `~/.tmux-sessionizer`) share the same 4-pane dev layout. When modifying the layout, update both files. Layout: yazi (top-left) | claude (top-middle, 1:1 ratio with yazi) | lazygit (right, 40 cols) | terminal (bottom-left, 16 rows).
