# Task: Create Figma to React Native Slash Command

## Overview

Create a Claude Code slash command that converts Figma designs to React Native code using the Figma Desktop MCP server. The command generates complete screens with React Native StyleSheet styling and extracts design tokens into a theme system.

## Requirements Summary

| Aspect | Decision |
|--------|----------|
| **Type** | Slash Command (`/figma-to-rn`) |
| **Location** | `~/.claude/commands/figma/to-rn.md` |
| **Figma Server** | Desktop MCP (`http://127.0.0.1:3845/mcp`) |
| **Output Framework** | React Native |
| **Code Detail** | Screen-level (complete screens with layout) |
| **Styling** | `StyleSheet.create()` |
| **Design Tokens** | Yes, generate theme constants |

## Architecture

### Command Location

```
~/.claude/commands/
└── figma/
    └── to-rn.md         # Main slash command
```

### Command Workflow

The `/figma-to-rn` command follows these phases:

1. **Validate Environment**
   - Check Figma Desktop MCP server is running at `127.0.0.1:3845`
   - Verify MCP tools are available
   - Provide setup instructions if not running

2. **Accept Input**
   - Figma frame URL or selection reference
   - Target directory for generated code
   - Optional: Component name override

3. **Extract Design System**
   - Use MCP to get colors, typography, spacing variables
   - Parse Figma styles into React Native format
   - Generate `theme.ts` with design tokens

4. **Analyze Frame Structure**
   - Get frame hierarchy via MCP
   - Identify component boundaries
   - Map Figma auto-layout to React Native Flexbox

5. **Generate Screen Code**
   - Create main screen component
   - Generate child components as needed
   - Apply StyleSheet styles from design tokens
   - Handle images, icons, and assets

6. **Review & Output**
   - Present generated code to user
   - Ask for feedback and refinements
   - Write files to target directory

## Implementation Details

### MCP Tool Usage

The Figma Desktop MCP provides these key capabilities:

```
Tools available at http://127.0.0.1:3845/mcp:
- get_file: Retrieve full Figma file data
- get_file_nodes: Get specific node/frame data
- get_image: Export images from frames
- get_style_metadata: Get color/text styles
- get_local_variables: Get design tokens/variables
```

### Design Token Mapping

| Figma Concept | React Native Output |
|---------------|---------------------|
| Color Variables | `theme.colors.*` |
| Typography Styles | `theme.typography.*` |
| Spacing Variables | `theme.spacing.*` |
| Corner Radius | `theme.borderRadius.*` |
| Effects/Shadows | `theme.shadows.*` |

### Layout Mapping

| Figma Auto-Layout | React Native Flexbox |
|-------------------|---------------------|
| Horizontal | `flexDirection: 'row'` |
| Vertical | `flexDirection: 'column'` |
| Space Between | `justifyContent: 'space-between'` |
| Packed (Start) | `justifyContent: 'flex-start'` |
| Packed (Center) | `justifyContent: 'center'` |
| Gap | `gap: value` |

### Generated File Structure

```
{target-directory}/
├── screens/
│   └── {ScreenName}Screen.tsx    # Main screen component
├── components/
│   └── {ComponentName}.tsx       # Extracted components
├── theme/
│   ├── index.ts                  # Theme exports
│   ├── colors.ts                 # Color tokens
│   ├── typography.ts             # Font styles
│   └── spacing.ts                # Spacing values
└── assets/
    └── images/                   # Exported images
```

## Command File Template

```markdown
---
description: Convert Figma designs to React Native code using Figma MCP
argument-hint: <figma-url-or-selection>
allowed-tools: [
  "mcp__figma__*",
  "Read",
  "Write",
  "Glob",
  "Bash(curl:*)"
]
---

# Figma to React Native

Convert Figma design to React Native: $ARGUMENTS

## Environment Check

Figma MCP Status: !`curl -s http://127.0.0.1:3845/mcp 2>/dev/null && echo "Connected" || echo "Not running"`

[Command instructions...]
```

## Implementation Checklist

### Phase 1: Command Structure
- [ ] Create `~/.claude/commands/figma/` directory
- [ ] Create `to-rn.md` command file
- [ ] Add YAML frontmatter with allowed-tools
- [ ] Add MCP connection validation

### Phase 2: Design Token Extraction
- [ ] Implement color extraction workflow
- [ ] Implement typography extraction
- [ ] Implement spacing extraction
- [ ] Generate `theme/` files template

### Phase 3: Layout Conversion
- [ ] Document Figma to Flexbox mapping
- [ ] Handle auto-layout conversion
- [ ] Handle absolute positioning
- [ ] Handle constraints/responsive

### Phase 4: Component Generation
- [ ] Screen component template
- [ ] Child component extraction logic
- [ ] StyleSheet generation patterns
- [ ] Image/asset handling

### Phase 5: Testing & Refinement
- [ ] Test with sample Figma files
- [ ] Handle edge cases (nested frames, variants)
- [ ] Add error handling for MCP failures
- [ ] Refine generated code quality

## MCP Server Setup Instructions

Include these in the command for users who haven't set up Figma MCP:

1. Open Figma Desktop app
2. Go to Preferences > Beta Features
3. Enable "MCP Server"
4. The server runs at `http://127.0.0.1:3845/mcp`

## Example Usage

```bash
# Convert a specific frame
/figma-to-rn https://www.figma.com/file/abc123/MyApp?node-id=1:234

# Convert currently selected frame (with Figma open)
/figma-to-rn --selection

# Specify output directory
/figma-to-rn https://figma.com/file/... --output ./src/screens
```

## Dependencies

- Figma Desktop App with MCP enabled (paid plan required)
- React Native project structure in target directory
- TypeScript support recommended

## Key Decisions Made

1. **Desktop MCP over Remote**: User preference for local server
2. **Screen-level generation**: Complete screens, not just components
3. **StyleSheet styling**: Standard RN styling, most compatible
4. **Theme extraction**: Generate reusable design tokens
5. **User commands location**: Personal command, available everywhere

## References

- [Figma MCP Server Docs](https://developers.figma.com/docs/figma-mcp-server/)
- [Figma MCP Guide](https://help.figma.com/hc/en-us/articles/32132100833559)
- [React Native StyleSheet](https://reactnative.dev/docs/stylesheet)

## Notes

- The Figma Desktop MCP requires a Dev/Full seat on a paid Figma plan
- MCP connection check should fail gracefully with setup instructions
- Consider Code Connect integration for design system components
