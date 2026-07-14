# Agentic SDLC Plugin for Claude Code

End-to-end SDLC workflow for Claude Code — from raw idea to implemented, tested, and shipped code.

Covers the full lifecycle: **grill → PRD → project constitution → features → test plan → issues → PMS → Ralph implementation loop**.

---

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add pratikjmistry/agentic-sdlc-plugin
```

### 2. Install the plugin

```bash
claude plugin install agentic-sdlc@agentic-sdlc-plugin
```

### 3. Reload plugins

```bash
/reload-plugins
```

### 4. (Optional) Connect PMS tools

The `/push-to-pms` skill requires a PMS connector MCP (GitHub Issues, Azure DevOps, Jira, Linear, or GitLab). Install the relevant connector from the Claude Code official marketplace:

```bash
# Examples
claude plugin install github@claude-plugins-official
claude plugin install atlassian@claude-plugins-official
claude plugin install linear@claude-plugins-official
```

---

## Workflows

### Greenfield (new project)

```
/agentic-sdlc:grill                          → Interrogate and clarify the idea
/agentic-sdlc:write-prd                      → Generate structured PRD
/agentic-sdlc:generate-project-constitution  → Interview + generate ai-context/ files
/agentic-sdlc:prd-to-features               → Decompose PRD into Features + User Stories
  ↓ HITL Feature Review
/agentic-sdlc:write-test-plan               → Generate TDD test plan (UT-, IT-, ST-, RT-)
  ↓ HITL Test Plan Review
/agentic-sdlc:feature-to-issues             → Decompose features into atomic issues
  ↓ HITL Issue Review
/agentic-sdlc:push-to-pms                   → Push issues to GitHub / Jira / Linear / ADO / GitLab
  ↓ Issues in PMS
```

### Brownfield (existing project, adding a feature)

```
/agentic-sdlc:grill                          → Interrogate the feature request
/agentic-sdlc:write-feature                  → Document the feature (no PRD needed)
  ↓ HITL Feature Review
/agentic-sdlc:feature-to-issues             → Decompose into issues
  ↓ HITL Issue Review
/agentic-sdlc:push-to-pms                   → Push to PMS
```

### Ralph implementation loop (after issues are in PMS)

```
claude --agent agentic-sdlc:ralph-impl      → Implement next unblocked DB/API/UI/INT issue
claude --agent agentic-sdlc:ralph-test      → Write integration tests (after impl issues close)
claude --agent agentic-sdlc:ralph-e2e       → Write E2E tests against staging (after tests close)
```

---

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| Grill | `/agentic-sdlc:grill` | Interrogates vague ideas into clear, buildable requirements |
| Write PRD | `/agentic-sdlc:write-prd` | Produces an implementation-ready Product Requirements Document |
| Generate Project Constitution | `/agentic-sdlc:generate-project-constitution` | Interviews you and generates `ai-context/` architecture files |
| PRD to Features | `/agentic-sdlc:prd-to-features` | Decomposes PRD into Features with User Stories |
| Write Feature | `/agentic-sdlc:write-feature` | Brownfield path — documents a single feature without a full PRD |
| Write Test Plan | `/agentic-sdlc:write-test-plan` | Generates a TDD test plan from FRs and ACs |
| Feature to Issues | `/agentic-sdlc:feature-to-issues` | Decomposes features into atomic, dependency-ordered issues |
| Push to PMS | `/agentic-sdlc:push-to-pms` | Creates issues in your chosen project management platform |

---

## Ralph Agents

Ralph agents are autonomous coding agents that pick up issues from the PMS and implement them.

| Agent | Command | Picks up | Triggers when |
|-------|---------|----------|---------------|
| Ralph-impl | `claude --agent agentic-sdlc:ralph-impl` | DB, API, UI, INT issues | Any unblocked impl issue exists |
| Ralph-test | `claude --agent agentic-sdlc:ralph-test` | TEST issues | All sibling impl issues are closed |
| Ralph-e2e | `claude --agent agentic-sdlc:ralph-e2e` | E2E issues | All sibling TEST issues are closed — **always run manually, never wired into CI** |

Handover between agents is **implicit via the dependency graph** in `ai-context/issues.json` — no manual handoff needed.

Each agent:
- Reads `ai-context/` for project context before touching code
- Asks for confirmation before starting work
- Creates a branch, implements, writes tests, opens a PR
- Waits for CI before merging
- Labels issues `needs-human` or `env-issue` if it gets stuck

### Ralph-impl parallelization

If `/generate-project-constitution` declared multiple DDD bounded contexts (domains) in
`ai-context/architecture.md`'s Domain Map, Ralph-impl runs as an **orchestrator** with two nested tiers of
parallelism:
- **Across domains:** each wave it spawns one domain-worker sub-agent per domain that currently has
  eligible issues, each in its own `git worktree`, so independent domains implement concurrently instead
  of one issue at a time. Capped by `Max parallel domain agents` (default 4).
- **Within a domain:** a domain worker stages its own issues by layer (DB → API → UI → INT); two or more
  issues in the same stage are, by construction, mutually independent (both were eligible at once, so
  neither blocks the other), so the domain worker spawns one nested issue-worker sub-agent per issue in
  that stage, each in a sibling `git worktree`. Capped by `Max parallel issue workers per stage` (default
  3). Occasional merge conflicts between siblings are expected and handled (rebase and retry), not a sign
  of a bug.

Both settings live in `ai-context/ralph-agent-spec.md`. Projects with a single domain (or no Domain Map,
or only one eligible issue in the current stage) fall back to the original fully-sequential loop
automatically.

### E2E tests are never part of the CI pipeline

`ai-context/testing.md`'s CI Gate covers unit, integration, lint, and traceability only. E2E/Playwright/
Cypress tests run in a separate workflow with a manual (`workflow_dispatch` or platform equivalent)
trigger — never `on: push` or `on: pull_request`. Ralph-e2e is always invoked by a human or manually
run once a feature's TEST issues close, typically once per feature-wave against staging.

> **Prerequisite:** Run `/agentic-sdlc:generate-project-constitution` first. Ralph agents require `ai-context/project-constitution.md` and related files to exist.

---

## Output Files

All planning artifacts are saved to `ai-context/` in your project repository:

| File | Produced by |
|------|-------------|
| `project-constitution.md` | `/generate-project-constitution` |
| `architecture.md` | `/generate-project-constitution` |
| `tech-stack.md` | `/generate-project-constitution` |
| `coding-standards.md` | `/generate-project-constitution` |
| `testing.md` | `/generate-project-constitution` |
| `database-guidelines.md` | `/generate-project-constitution` |
| `security.md` | `/generate-project-constitution` |
| `ralph-agent-spec.md` | `/generate-project-constitution` |
| `issues.json` | `/feature-to-issues` |
| `pms-map.json` | `/push-to-pms` |

Feature specs are saved to `docs/features/`:

| File | Produced by |
|------|-------------|
| `feature-summary.md` | `/prd-to-features` |
| `F-XX-slug.md` | `/prd-to-features` |
| `test-plan.md` | `/write-test-plan` |

---

## HITL Checkpoints

Each major step ends with a Human-in-the-Loop review checkpoint. Do not proceed to the next step until you have explicitly confirmed the output.

---

## Updating the Plugin

To pull the latest version:

```bash
claude plugin marketplace update agentic-sdlc-plugin
/reload-plugins
```
