---
name: git-rebase-help
description: 'Use this skill when the user invokes `git-rebase-help`, mentions rebasing a branch, asks how to bring a branch up to date, or needs mid-rebase conflict help. Triggers on: "git-rebase-help", "rebase this branch", "bring this branch up to date", "mid-rebase conflict help", or similar Git rebase workflow requests. Guide the workflow step-by-step through repository checks, target branch selection, working tree preparation, conflict resolution, and post-rebase cleanup, with confirmation required before any history-rewriting, content-changing, or destructive Git action.'
---

# Git Rebase Help

Safety-first guidance for conversational Git rebase workflows.

This skill is ask-first by default. Use read-only Git checks to understand the
state, explain what was found, then ask the user for one decision at a time
before any state-changing or history-rewriting action.

Use this skill to:

- detect whether a rebase is already in progress
- prepare the working tree before rebasing
- choose how to handle uncommitted work
- rebase onto the correct target branch
- resolve conflicts file-by-file and block-by-block
- continue, skip, or abort safely
- restore stashed work after the rebase if needed
- finish with safe push guidance

This skill is generic and reusable across environments. It must not depend on a
specific model vendor, editor, or coding agent runtime.

Treat the workflow as an iterative loop:

- inspect the current rebase state
- ask the next decision question
- resolve one conflicted file at a time
- resolve one conflict block at a time within that file
- stage only after approval
- ask before continuing, skipping, aborting, applying a stash, or pushing
- repeat until the rebase completes or the user intentionally stops

## Core Principles

- Ask one decision at a time.
- Use plain language unless the user starts with more advanced Git terms.
- Run read-only checks without confirmation when they help orient the workflow.
- Explain and confirm every history-rewriting, content-changing, or destructive action before running it.
- After each read-only check, explain what it means before asking for the next decision.
- Never assume the target branch when there is ambiguity.
- Never continue a rebase while conflict markers remain unresolved.
- Never recommend `git push --force`; use `--force-with-lease` instead.
- Prefer safe, reversible steps.
- If something unexpected happens, stop and explain before continuing.

## Read-Only Checks Allowed Without Confirmation

These commands do not change repository state and may be run without confirmation:

```bash
git rev-parse --is-inside-work-tree
git status
git status --short
git branch --show-current
git diff --name-only --diff-filter=U
git log --oneline --decorate -n 10
git branch -a
git remote -v
git ls-remote --heads origin
```

If needed, inspect file contents or search conflict markers as part of read-only analysis.

Everything else requires explanation first and explicit user approval before execution.

## Step 1 - Validate Repository State

Run:

```bash
git rev-parse --is-inside-work-tree
```

If the current directory is not a Git repository:

- stop
- explain that this skill only works inside a Git repository

Then run:

```bash
git status
```

If a rebase is already in progress:

- skip directly to the conflict resolution loop

Then run:

```bash
git branch --show-current
```

Tell the user the current branch.

## Step 2 - Choose Rebase Target

Ask which branch should be the rebase target.

Suggested default:

- `origin/main`

If the repository clearly uses another integration branch such as:

- `origin/develop`
- `origin/master`

mention it as an option, but do not silently switch defaults.

If the user does not specify a target, ask once and offer the default suggestion.

Validate that the target exists before rebasing. Prefer:

```bash
git ls-remote --exit-code --heads origin <target-branch>
```

If the remote target does not exist:

- explain the issue
- ask the user to choose another branch

## Step 3 - Check Branch State

Inspect whether the current branch has local work, unpushed commits, or a dirty working tree.

Useful checks:

```bash
git status --short
git log origin/<current-branch>..HEAD --oneline
```

If there are unpushed commits:

- warn that a successful rebase will likely require a later push with `--force-with-lease`
- do not block progress

## Step 4 - Handle Working Directory State

### Case A - Clean Working Tree

If there are no staged, unstaged, or untracked changes:

- proceed to rebase

### Case B - Uncommitted Changes Exist

Explain that rebase works on commits and the user must decide how to handle current changes first.

Ask the user to choose one option:

1. Commit current changes so they are included in the rebased history
2. Stash current changes so they stay out of the rebase for now
3. Cancel

#### Option 1 - Commit

Use when the user wants the current work included in the rebased history.

Typical commands:

```bash
git add .
git commit -m "WIP: before rebase"
```

Run only after confirmation.

#### Option 2 - Stash

Use when the current work is unfinished, experimental, or unrelated.

Typical command:

```bash
git stash push -u -m "pre-rebase-<timestamp>"
```

Run only after confirmation.

Record that a stash was created so the user can be prompted to restore it later.

#### Option 3 - Cancel

Stop and summarize what the user needs to do manually.

## Step 5 - Start Rebase

Before rebasing, show the exact commands and ask for confirmation.

Typical sequence:

```bash
git fetch origin
git rebase <target-branch>
```

If the rebase completes without conflicts:

- move to completion

If the rebase stops on conflicts:

- enter the conflict resolution loop

If Git returns another error:

- stop
- explain the error
- ask how the user wants to proceed

## Conflict Resolution Loop

Run:

```bash
git diff --name-only --diff-filter=U
```

Tell the user how many conflicted files exist.

Process conflicted files one at a time.

After each `git rebase --continue`, check again for newly conflicted files and
repeat this loop until the rebase completes, pauses on another issue, or the
user chooses to skip or abort.

## Per-File Conflict Handling

For each conflicted file:

1. Tell the user the file path.
2. Ask whether to inspect and resolve it now.
3. If the user wants to handle it manually, wait until they confirm it is resolved, then verify conflict markers are gone before staging.
4. Do not move to the next conflicted file until the current file is either resolved and staged, intentionally skipped as part of the rebase flow, or left for the user to finish manually.

To inspect conflict locations, use read-only commands such as:

```bash
grep -n "<<<<<<<\\|=======\\|>>>>>>>" <file>
```

Inspect surrounding context as needed to understand the intent of both sides.

## Per-Block Conflict Handling

Handle one conflict block at a time.

For each block:

1. Show the conflicting section with enough surrounding context to understand it.
2. Explain both sides in plain language.
3. Make it explicit that during a rebase:
   `HEAD` is the target branch state.
   The other side is the user commit being replayed.
4. Suggest one of these strategies:
   keep the target branch version
   keep the replayed commit version
   combine both
   resolve manually
5. Ask the user what to do.

Suggested choices:

1. Keep target branch version
2. Keep replayed commit version
3. Keep both
4. Edit manually

If generating a merged version:

- show it clearly
- ask for confirmation before writing it

After the user approves the resolution:

- update the file
- remove conflict markers
- verify the block is clean

If multiple conflict blocks exist in the same file, repeat this process block by
block until the file is fully resolved.

Continue until all blocks in the file are resolved.

Then stage the file:

```bash
git add <file>
```

Only stage after confirmation or explicit approval.

After a file is staged, move to the next conflicted file and repeat the same
process until no conflicted files remain for the current rebase stop.

## Continue Rebase

After all conflicted files in the current stop are resolved and staged, ask before running:

```bash
git rebase --continue
```

Possible outcomes:

### A. Rebase Continues Successfully

- if no further conflicts appear, move to completion
- if new conflicts appear, return to the top of the conflict resolution loop

### B. Empty Commit During Rebase

If Git reports that the current commit is empty because the changes already exist, explain that in plain language and offer these choices:

1. Skip this commit
2. Keep it as an empty commit if the workflow requires it
3. Abort the rebase

Typical commands:

```bash
git rebase --skip
```

or, if the environment supports it and the user explicitly wants to preserve an empty commit:

```bash
GIT_EDITOR=true git rebase --continue
```

Run only after confirmation.

### C. Another Error

Stop and explain the error. Do not guess.

## Completion

When the rebase finishes:

- say the rebase is complete
- remind the user which target branch was used

If a stash was created earlier:

- ask whether to restore it now

Typical command:

```bash
git stash pop
```

If stash restoration creates conflicts:

- explain that these are stash-application conflicts, not rebase conflicts
- resolve them with the same per-file and per-block method

If the current branch had unpushed commits before or the rebase rewrote history:

- remind the user that they will likely need to push with:

```bash
git push --force-with-lease origin <current-branch>
```

Ask before running that command.

## Escape Hatches

At any point, the user may ask for:

### Abort Rebase

```bash
git rebase --abort
```

If a stash was created earlier, remind the user that it still exists and can be restored later.

### Skip Current Commit

```bash
git rebase --skip
```

### Show Status

```bash
git status
```

### Explain Current Step

Summarize:

- whether a rebase is running
- current target branch
- whether unresolved conflicts remain
- whether a stash exists
- the next safe action

## Safety Rules

- Never auto-resolve a conflict without confirmation.
- Never run content-changing commands without showing them first.
- Never continue rebasing if conflict markers still exist.
- Never force-push with `--force`.
- Always prefer `--force-with-lease`.
- Never assume uncommitted changes should be committed.
- Never assume the default target branch if the repository state suggests ambiguity.
- If editing a file, explain the intended resolution first.
- If anything is unclear, stop and ask instead of guessing.

## Minimal Success Criteria

This skill is successful when it can reliably:

- detect whether a rebase is already in progress
- identify the target branch
- help the user prepare the working tree
- start the rebase safely
- explain conflicts clearly
- resolve conflicts block-by-block with approval
- continue until the rebase is complete or intentionally aborted
- restore stashed work if requested
- remind the user about safe push behavior after rewritten history
