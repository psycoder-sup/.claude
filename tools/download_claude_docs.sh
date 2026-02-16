#!/bin/bash

# Download Claude Code Documentation
# Downloads all markdown files from https://code.claude.com/docs/en/

OUTPUT_DIR="docs"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# List of all documentation files from llms.txt
DOCS=(
    "amazon-bedrock"
    "analytics"
    "checkpointing"
    "chrome"
    "claude-code-on-the-web"
    "cli-reference"
    "common-workflows"
    "costs"
    "data-usage"
    "desktop"
    "devcontainer"
    "discover-plugins"
    "github-actions"
    "gitlab-ci-cd"
    "google-vertex-ai"
    "headless"
    "hooks"
    "hooks-guide"
    "iam"
    "interactive-mode"
    "jetbrains"
    "legal-and-compliance"
    "llm-gateway"
    "mcp"
    "memory"
    "microsoft-foundry"
    "model-config"
    "monitoring-usage"
    "network-config"
    "output-styles"
    "overview"
    "plugin-marketplaces"
    "plugins"
    "plugins-reference"
    "quickstart"
    "sandboxing"
    "security"
    "settings"
    "setup"
    "skills"
    "slack"
    "slash-commands"
    "statusline"
    "sub-agents"
    "terminal-config"
    "third-party-integrations"
    "troubleshooting"
    "vs-code"
)

BASE_URL="https://code.claude.com/docs/en"

echo "Downloading Claude Code documentation..."
echo "Output directory: $OUTPUT_DIR"
echo ""

total=${#DOCS[@]}
count=0

for doc in "${DOCS[@]}"; do
    count=$((count + 1))
    url="${BASE_URL}/${doc}.md"
    output_file="${OUTPUT_DIR}/${doc}.md"

    printf "[%2d/%d] Downloading %s.md..." "$count" "$total" "$doc"

    if curl -fsSL "$url" -o "$output_file" 2>/dev/null; then
        echo " done"
    else
        echo " failed"
    fi
done

echo ""
echo "Download complete! Files saved to: $OUTPUT_DIR"
echo "Total files: $(ls -1 "$OUTPUT_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')"
