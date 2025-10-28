#!/usr/bin/env bash
# create_repo.sh — initialize git, create GitHub repo with gh, and push
# Usage:
#   ./create_repo.sh
# or override:
#   REPO_OWNER=youruser REPO_NAME=repo PRIVATE=true ./create_repo.sh

set -euo pipefail

REPO_OWNER="${REPO_OWNER:-dhkiller350}"
REPO_NAME="${REPO_NAME:-pythonfirewall}"
PRIVATE="${PRIVATE:-false}"   # "true" or "false"
GIT_BRANCH="${GIT_BRANCH:-main}"

# Check prerequisites
if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI 'gh' not found. Install it: https://cli.github.com/"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git not found. Install git and try again."
  exit 1
fi

echo "Checking gh authentication..."
if ! gh auth status >/dev/null 2>&1; then
  echo "You are not authenticated with gh. Run: gh auth login"
  exit 1
fi

# Initialize repo (if not already)
if [ ! -d .git ]; then
  git init
else
  echo "Existing .git found — using current repository"
fi

# Create main branch
git checkout -B "$GIT_BRANCH"

# Staging and commit
git add --all
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "Existing commit history detected. Creating a new commit."
  git commit -m "Update pythonfirewall" || echo "No changes to commit"
else
  git commit -m "Initial pythonfirewall" || true
fi

# Create GitHub repo and push
VISIBILITY="--public"
if [ "$PRIVATE" = "true" ]; then
  VISIBILITY="--private"
fi

echo "Creating repository ${REPO_OWNER}/${REPO_NAME} on GitHub (visibility: $VISIBILITY)..."
gh repo create "${REPO_OWNER}/${REPO_NAME}" $VISIBILITY --source=. --remote=origin --push

echo "Repository created and pushed: https://github.com/${REPO_OWNER}/${REPO_NAME}"
echo "Done."
