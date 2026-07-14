---
name: report-bug
description: "Use this skill when the user types /report-bug or says 'report a bug', 'I found a bug', 'log a bug', 'there's a bug in...', or wants to record a defect. Handles two phases: (1) REPORT — collects bug details, checks for duplicates (High/Critical only), searches the codebase for affected files and test coverage gaps, then creates a structured GitHub issue with [BUG][SEVERITY] title and severity label; (2) FIX — triggered when the user says 'fix bug #NNN' or 'fix this bug', creates a branch, applies the fix, runs tests, opens a PR, merges on CI pass, and auto-closes the issue with a fix summary comment. Also serves as the unified defect format for ralph-test and ralph-e2e when they log defects manually."
---

# /report-bug — Bug Reporting and Fix Skill

## Workflow Overview

`/report-bug` operates in two distinct phases. Phase 1 always runs when a bug is reported. Phase 2 runs only when the user explicitly asks to fix a bug.

```
REPORT PHASE:
  /report-bug → collect details → duplicate check (High/Critical) →
  codebase search → test coverage check → create GitHub issue → done

FIX PHASE (triggered separately):
  "fix bug #NNN" → read issue → branch → implement fix →
  run tests → PR → CI → merge → auto-close issue with comment
```

**Prerequisites:** `ai-context/pms-map.json` must exist (produced by `/push-to-pms`). The `repo` field is used to target the correct GitHub repository.

---

## PHASE 1 — Report a Bug

### Step R1 — Collect Bug Details

Use `AskUserQuestion` to collect the required fields in one interaction:

**Call `AskUserQuestion` with:**
- question: "What is the severity of this bug?"
- header: "Severity"
- options:
  1. **Critical** — System is down, data loss, or security breach. No workaround.
  2. **High** — Core feature is broken. Workaround exists but painful.
  3. **Medium** — Feature partially broken. Reasonable workaround available.
  4. **Low** — Minor issue, cosmetic, or edge case. No user impact.

Then collect the following as free text (ask in a single follow-up message, not one by one):

```
- Description: What went wrong? (1-3 sentences)
- Steps to reproduce: Numbered list of exact steps to trigger the bug
- Expected behaviour: What should have happened
- Actual behaviour: What actually happened
- Environment: Where was this found? (production / staging / local / specify)
```

If the bug was triggered by a ralph-test or ralph-e2e defect log (user pastes a `[BUG][IT-NNN]` or `[BUG][E2E-NNN]` report), extract all fields automatically from the pasted content — do not ask questions the defect log already answers.

---

### Step R2 — Duplicate Check (High and Critical only)

For **High** and **Critical** severity bugs only: search the GitHub repo for existing open issues that may describe the same bug.

Search using keywords from the description and affected area:
```
# Use GitHub issue search via PMS tools or GitHub MCP
Search: is:issue is:open label:bug [keywords from description]
```

If matches are found, present them:

> **Possible duplicates found — please review before creating a new issue:**
>
> - #NNN [title] — [created date]
> - #NNN [title] — [created date]
>
> Are any of these the same bug? Reply with the issue number to link instead of creating new, or type **NEW** to create a separate issue.

If the user identifies a duplicate: add a comment on the existing issue with the additional reproduction details and stop. Do not create a new issue.

If no duplicates found or user confirms **NEW**: proceed to Step R3.

For **Medium** and **Low** severity: skip duplicate check and proceed directly to Step R3.

---

### Step R3 — Codebase Verification

Search the repository codebase to identify which files and functions are most likely responsible for the bug.

Use keyword search based on the affected feature area and description:
```
# Search codebase for related code
- Search for functions, components, or modules referenced in the bug description
- Search for route handlers, API endpoints, or DB queries related to the affected flow
- Identify the 2-5 most likely files involved
```

Present findings:

> **Codebase search — likely affected areas:**
>
> | File | Reason |
> |------|--------|
> | `src/auth/google.ts` | Handles Google OAuth callback — matches described flow |
> | `src/middleware/session.ts` | Session creation — called after OAuth success |
>
> Confirm these look right, or describe the affected area if different.

Wait for confirmation or correction. Update the affected file list based on user response.

---

### Step R4 — Test Coverage Check

For each identified file, check whether tests exist that should have caught this bug:

```
# Look for test files related to the affected files
- Check __tests__/, *.test.ts, *.spec.ts adjacent to affected files
- Check integration test directories for IT- tests covering the affected flow
- Check E2E test files for E2E- tests covering the affected user journey
```

Summarise the coverage gap:

> **Test coverage assessment:**
>
> - `src/auth/google.ts` — Unit tests exist in `auth.test.ts` but do not cover the error path in Step 3
> - No integration test covers the full OAuth callback → session creation flow
> - E2E-004 (Google sign-in E2E flow) should have caught this but may not be running against staging
>
> Coverage gap will be noted in the bug issue.

---

### Step R5 — Create GitHub Issue

Create a GitHub issue in the repo from `ai-context/pms-map.json` with the following structure:

**Title format:**
```
[BUG][SEVERITY] Brief description of what is broken
```
Examples:
```
[BUG][CRITICAL] User session not created after Google OAuth callback
[BUG][HIGH] Watchlist fails to load when user has more than 50 stocks
[BUG][MEDIUM] Price table shows stale data after symbol search
[BUG][LOW] Tooltip flickers on hover in StockDetailPanel
```

**Labels to apply:**
- `bug`
- `severity:critical` / `severity:high` / `severity:medium` / `severity:low`
- `needs-triage` (removed when fix is assigned)

**Issue body template:**
```markdown
## Bug Report

**Severity:** [Critical / High / Medium / Low]
**Environment:** [production / staging / local / other]
**Reported by:** [user or "ralph-test" / "ralph-e2e" if automated]

---

## Description

[Description from Step R1]

---

## Steps to Reproduce

1. [Step 1]
2. [Step 2]
3. ...

---

## Expected Behaviour

[Expected from Step R1]

---

## Actual Behaviour

[Actual from Step R1]

---

## Affected Files (from codebase search)

- `[file path]` — [reason]
- `[file path]` — [reason]

---

## Test Coverage Gap

[Summary from Step R4 — which tests are missing or insufficient]

---

## Fix Notes

_To be completed when fix is implemented._

To fix this bug, run: `fix bug #[issue number]`
```

After creating the issue, present a summary:

> **Bug logged: #[NNN] — [title]**
> URL: [GitHub issue URL]
>
> **Next step:** When ready to fix, say `fix bug #[NNN]` and I will implement the fix, open a PR, and close this issue on merge.

---

## PHASE 2 — Fix a Bug

Triggered when the user says:
- `fix bug #NNN`
- `fix this bug`
- `fix #NNN`
- `implement fix for [bug description]`

### Step F1 — Read the Bug Issue

Fetch the GitHub issue by number from the repo in `ai-context/pms-map.json`. Extract:
- Affected files list
- Description and reproduction steps
- Severity
- Test coverage gap

If no affected files are listed in the issue, run Step R3 now before proceeding.

---

### Step F2 — Create Fix Branch

```bash
git checkout main && git pull
git checkout -b fix/[issue-number]-[slug]
```

Example: `fix/42-google-oauth-session-not-created`

---

### Step F3 — Implement the Fix

Read the affected files. Apply the minimal change that resolves the bug without introducing regressions.

Rules:
- Fix only what the bug describes — do not refactor unrelated code
- Follow `ai-context/coding-standards.md` (load via QMD if available)
- If the fix requires a DB migration, follow `ai-context/database-guidelines.md`
- If the fix touches the auth/security layer, note it explicitly in the PR

---

### Step F4 — Write or Update Tests

For every test coverage gap identified in the bug issue:
- Write a test that would have caught this bug
- Name the test to reference the bug: `"[BUG-NNN] [describes the broken behaviour]"`
- Run the full test suite to verify the fix passes and no regressions are introduced

```bash
# Run tests per ai-context/testing.md
[test runner command]
```

If tests fail for reasons unrelated to this bug: note them in the PR but do not block the merge.

---

### Step F5 — Commit, Open PR, Merge

Commit message:
```
fix(#[NNN]): [brief description of fix]

Fixes [BUG][SEVERITY] — [bug title]

Root cause: [1-2 sentences]
Fix: [1-2 sentences]
Tests added: [test names or "none required"]
```

PR title:
```
fix: [BUG][SEVERITY] [bug title] (#NNN)
```

PR body:
```markdown
## Fix Summary

**Bug:** #[NNN] — [title]
**Severity:** [level]
**Root cause:** [explanation]
**Fix:** [what was changed and why]

## Tests Added

- [test name]: [what it verifies]

## Affected Files

- [file] — [what changed]

Closes #[NNN]
```

Wait for CI. **Do not merge if CI is failing.** Once CI passes, merge.

---

### Step F6 — Auto-Close Issue with Comment

After the PR is merged, post a comment on the bug issue and close it:

**Comment:**
```
✅ Fixed in PR #[PR-number] — merged [date].

**Root cause:** [from commit message]
**Fix:** [from commit message]
**Tests added:** [list]

The fix is live on [branch/environment]. Verify on staging if required.
```

Then close the GitHub issue. Remove `needs-triage` label if still present.

---

## FAILURE HANDLING

| Situation | Action |
|-----------|--------|
| `pms-map.json` not found | Halt: "Run /push-to-pms first to configure the GitHub repo." |
| GitHub API error creating issue | Retry once. Report the error if it persists. |
| Fix introduces new test failures | Note in PR, do not merge. Label issue `needs-human`. Report. |
| CI fails on fix PR | Diagnose and fix CI failure up to 2 attempts. If still failing, label `needs-human`, describe the failure, and halt. |
| Affected files cannot be identified | Ask the user to point to the relevant files before proceeding with the fix. |
| Duplicate found but user wants NEW anyway | Create new issue and add a cross-reference comment: "See also: #[duplicate-number]" |

---

## Integration with Ralph Agents

When ralph-test or ralph-e2e discover defects, they already create GitHub issues in their own format (`[BUG][IT-NNN]` / `[BUG][E2E-NNN]`). The `/report-bug` skill is the equivalent for manually reported bugs.

Bug issues created by `/report-bug` are **not** in `ai-context/issues.json` (they are unplanned). Ralph-impl does not pick them up automatically. The fix is always triggered explicitly: `fix bug #NNN`.
