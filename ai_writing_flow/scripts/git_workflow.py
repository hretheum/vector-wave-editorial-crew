#!/usr/bin/env python3
"""
Git-based Development Workflows - Task 13.2

Provides standardized git workflows for AI Writing Flow development.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import re
import json
from datetime import datetime


class GitWorkflow:
    """Git workflow automation for development"""
    
    def __init__(self):
        self.repo_root = Path.cwd()
        self.valid_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
        self.valid_scopes = ["agents", "flow", "kb", "tools", "monitoring", 
                            "optimization", "config", "ui", "crewai"]
    
    def setup_git_config(self):
        """Setup git configuration for the project"""
        print("🔧 Setting up git configuration...")
        
        # Set commit template
        template_path = self.repo_root / ".gitmessage"
        if template_path.exists():
            subprocess.run(["git", "config", "--local", "commit.template", ".gitmessage"])
            print("✅ Commit template configured")
        
        # Setup helpful aliases
        aliases = [
            ("flow-status", "!git status && echo && git log --oneline -5"),
            ("flow-diff", "diff --staged --stat"),
            ("flow-commit", "commit -v"),
            ("flow-push", "push -u origin HEAD"),
            ("flow-sync", "!git fetch && git rebase origin/main"),
            ("flow-feature", "checkout -b"),
            ("flow-pr", "!gh pr create --fill")
        ]
        
        for alias, command in aliases:
            subprocess.run(["git", "config", "--local", f"alias.{alias}", command])
        
        print("✅ Git aliases configured")
        print("\nAvailable aliases:")
        for alias, _ in aliases:
            print(f"  - git {alias}")
    
    def create_feature_branch(self, feature_name: str, issue_number: Optional[int] = None):
        """Create a feature branch with standard naming"""
        # Sanitize feature name
        branch_name = re.sub(r'[^a-zA-Z0-9-]', '-', feature_name.lower())
        branch_name = re.sub(r'-+', '-', branch_name).strip('-')
        
        if issue_number:
            branch_name = f"feature/{issue_number}-{branch_name}"
        else:
            branch_name = f"feature/{branch_name}"
        
        # Create and checkout branch
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            print(f"✅ Created branch: {branch_name}")
            
            # Create initial commit message template
            commit_msg = f"feat: {feature_name}\n\n"
            if issue_number:
                commit_msg += f"Resolves #{issue_number}\n"
            
            return branch_name
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create branch: {e}")
            return None
    
    def validate_commit_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """Validate commit message format"""
        lines = message.strip().split('\n')
        if not lines:
            return False, "Empty commit message"
        
        subject = lines[0]
        
        # Check format: type(scope): subject
        pattern = r'^(' + '|'.join(self.valid_types) + r')(\((' + '|'.join(self.valid_scopes) + r')\))?: .+$'
        
        if not re.match(pattern, subject):
            return False, f"Invalid format. Use: type(scope): subject\nValid types: {', '.join(self.valid_types)}\nValid scopes: {', '.join(self.valid_scopes)}"
        
        # Check subject length
        if len(subject) > 72:
            return False, f"Subject too long ({len(subject)} chars). Max 72 chars."
        
        # Check imperative mood (basic check)
        type_match = re.match(r'^[^:]+:\s*(.+)$', subject)
        if type_match:
            verb = type_match.group(1).split()[0].lower()
            if verb.endswith('ed') or verb.endswith('ing'):
                return False, "Use imperative mood (e.g., 'add' not 'added' or 'adding')"
        
        return True, None
    
    def create_pr_template(self) -> str:
        """Create a pull request template"""
        template = """## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated

## Related Issues
Closes #

## Screenshots (if applicable)
"""
        return template
    
    def check_branch_status(self) -> dict:
        """Check current branch status"""
        try:
            # Get current branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True
            ).stdout.strip()
            
            # Get status
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True
            ).stdout
            
            # Get commits ahead/behind
            ahead_behind = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"],
                capture_output=True,
                text=True
            ).stdout.strip()
            
            behind, ahead = (0, 0)
            if ahead_behind:
                parts = ahead_behind.split()
                if len(parts) == 2:
                    behind, ahead = int(parts[0]), int(parts[1])
            
            return {
                "branch": branch,
                "has_changes": bool(status),
                "changes_count": len(status.splitlines()),
                "ahead": ahead,
                "behind": behind
            }
        except Exception as e:
            return {"error": str(e)}
    
    def generate_changelog(self, since_tag: Optional[str] = None) -> str:
        """Generate changelog from commits"""
        cmd = ["git", "log", "--pretty=format:%H|%s|%an|%ad", "--date=short"]
        
        if since_tag:
            cmd.append(f"{since_tag}..HEAD")
        else:
            cmd.append("-20")  # Last 20 commits
        
        try:
            output = subprocess.run(cmd, capture_output=True, text=True).stdout
            
            # Parse commits
            commits_by_type = {
                "feat": [],
                "fix": [],
                "docs": [],
                "style": [],
                "refactor": [],
                "test": [],
                "chore": []
            }
            
            for line in output.splitlines():
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 4:
                    hash_short = parts[0][:7]
                    subject = parts[1]
                    author = parts[2]
                    date = parts[3]
                    
                    # Extract type
                    match = re.match(r'^(\w+)(?:\([^)]+\))?: (.+)$', subject)
                    if match and match.group(1) in commits_by_type:
                        commit_type = match.group(1)
                        message = match.group(2)
                        commits_by_type[commit_type].append(
                            f"- {message} ({hash_short})"
                        )
            
            # Generate changelog
            changelog = f"## Changelog\n\n"
            changelog += f"Generated on {datetime.now().strftime('%Y-%m-%d')}\n\n"
            
            type_names = {
                "feat": "✨ Features",
                "fix": "🐛 Bug Fixes",
                "docs": "📚 Documentation",
                "style": "💄 Style",
                "refactor": "♻️ Refactoring",
                "test": "✅ Tests",
                "chore": "🔧 Chores"
            }
            
            for commit_type, commits in commits_by_type.items():
                if commits:
                    changelog += f"### {type_names[commit_type]}\n\n"
                    changelog += "\n".join(commits) + "\n\n"
            
            return changelog
            
        except Exception as e:
            return f"Error generating changelog: {e}"


def create_git_hooks():
    """Create git hooks for the project"""
    hooks_dir = Path(".git/hooks")
    
    # Pre-push hook
    pre_push_hook = """#!/bin/bash
# Pre-push hook for AI Writing Flow

echo "🔍 Running pre-push checks..."

# Run tests
echo "Running tests..."
make test > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Push aborted."
    echo "Run 'make test' to see failures."
    exit 1
fi

# Run linting
echo "Running linters..."
make lint > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Linting failed. Push aborted."
    echo "Run 'make lint' to see issues."
    exit 1
fi

echo "✅ All checks passed!"
"""
    
    # Commit-msg hook
    commit_msg_hook = '''#!/usr/bin/env python3
import sys
import re

def validate_commit_message(message):
    """Validate commit message format"""
    lines = message.strip().split('\\n')
    if not lines:
        return False, "Empty commit message"
    
    subject = lines[0]
    valid_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
    valid_scopes = ["agents", "flow", "kb", "tools", "monitoring", "optimization", "config", "ui", "crewai"]
    
    # Check format
    pattern = r'^(' + '|'.join(valid_types) + r')(\\((' + '|'.join(valid_scopes) + r')\\))?: .+$'
    
    if not re.match(pattern, subject):
        return False, f"Invalid format. Use: type(scope): subject"
    
    # Check length
    if len(subject) > 72:
        return False, f"Subject too long ({len(subject)} chars). Max 72."
    
    return True, None

# Read commit message
with open(sys.argv[1], 'r') as f:
    message = f.read()

# Validate
valid, error = validate_commit_message(message)
if not valid:
    print(f"❌ Invalid commit message: {error}")
    print("Example: feat(agents): add research capabilities")
    sys.exit(1)
'''
    
    # Write hooks
    pre_push_path = hooks_dir / "pre-push"
    with open(pre_push_path, 'w') as f:
        f.write(pre_push_hook)
    pre_push_path.chmod(0o755)
    
    commit_msg_path = hooks_dir / "commit-msg"
    with open(commit_msg_path, 'w') as f:
        f.write(commit_msg_hook)
    commit_msg_path.chmod(0o755)
    
    print("✅ Git hooks created")


def main():
    """Main entry point for git workflow setup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git workflow helper")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup git configuration")
    
    # Feature command
    feature_parser = subparsers.add_parser("feature", help="Create feature branch")
    feature_parser.add_argument("name", help="Feature name")
    feature_parser.add_argument("--issue", type=int, help="Issue number")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check branch status")
    
    # Changelog command
    changelog_parser = subparsers.add_parser("changelog", help="Generate changelog")
    changelog_parser.add_argument("--since", help="Since tag/commit")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate commit message")
    validate_parser.add_argument("message", help="Commit message to validate")
    
    args = parser.parse_args()
    
    workflow = GitWorkflow()
    
    if args.command == "setup":
        workflow.setup_git_config()
        create_git_hooks()
    elif args.command == "feature":
        workflow.create_feature_branch(args.name, args.issue)
    elif args.command == "status":
        status = workflow.check_branch_status()
        print(json.dumps(status, indent=2))
    elif args.command == "changelog":
        changelog = workflow.generate_changelog(args.since)
        print(changelog)
    elif args.command == "validate":
        valid, error = workflow.validate_commit_message(args.message)
        if valid:
            print("✅ Valid commit message")
        else:
            print(f"❌ {error}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()