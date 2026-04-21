# Git Rebase Help Skill

This skill helps an agent guide a user through a Git rebase safely. It is
conversational and ask-first, with confirmation required before any
history-rewriting or state-changing Git action.

## What It Does

- checks whether a rebase is already in progress
- helps choose the target branch
- handles clean vs dirty working tree decisions
- guides commit or stash choices before rebasing
- resolves conflicts file-by-file and block-by-block
- asks before continue, skip, abort, stash pop, and push steps

## How To Use

Use this skill when the task is about rebasing a branch or resolving a rebase
that already stopped on conflicts.

Examples:

- "git-rebase-help"
- "Help me rebase this branch onto main"
- "Bring this branch up to date with origin/main"
- "I am in the middle of a rebase and need conflict help"

Open [SKILL.md](./SKILL.md) and follow the step-by-step rebase workflow.
