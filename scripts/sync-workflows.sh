#!/bin/bash
# Workflow Synchronization Script
# Purpose: Create symlinks from .claude/commands/ to .agent/workflows/
# Constitution: v2.7 Law #6 (LLM Enforcement - Workflow First)

set -e

WORKFLOWS_DIR=".agent/workflows"
CLAUDE_COMMANDS_DIR=".claude/commands"

echo "🔄 Syncing workflows: ${WORKFLOWS_DIR} -> ${CLAUDE_COMMANDS_DIR}"

# Create .claude/commands directory if not exists
mkdir -p "${CLAUDE_COMMANDS_DIR}"

# Remove existing symlinks to avoid stale links
echo "🧹 Cleaning up old symlinks..."
find "${CLAUDE_COMMANDS_DIR}" -type l -delete

# Create symlinks for all workflow files (except README.md)
echo "🔗 Creating symlinks..."
count=0
for workflow in ${WORKFLOWS_DIR}/*.md; do
    filename=$(basename "$workflow")

    # Skip README.md (meta-documentation)
    if [ "$filename" = "README.md" ]; then
        continue
    fi

    # Create symlink with relative path
    ln -sf "../../${workflow}" "${CLAUDE_COMMANDS_DIR}/${filename}"
    echo "  ✓ /${filename%.md}"
    count=$((count + 1))
done

echo ""
echo "✅ Synced ${count} workflows to Claude Code commands"
echo ""
echo "Available slash commands:"
echo "  /create-issue"
echo "  /run-gap-analysis"
echo "  /council-review"
echo "  /create-rfc"
echo "  /create-spec"
echo "  /activate-deferred"
echo "  /create-roadmap"
echo "  /brainstorm"
echo "  /amend-constitution"
echo "  /hotfix"
echo "  /merge-to-develop"
echo ""
echo "Constitution: ai-rules.md v2.7 Law #6 (Workflow First)"
