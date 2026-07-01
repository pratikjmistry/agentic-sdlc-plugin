# Template: project-constitution.md

## Purpose
Master governance document. Always generated **last** — after all detailed files exist so it can accurately reference them. Must be readable in under 5 minutes.

## Required Sections

- **Project identity** — name, one-line description, status (greenfield / active / legacy)
- **Immutable principles** — the 3–5 non-negotiable rules from Q27. Write as explicit, enforceable statements, not aspirations. These cannot be overridden by any team member or AI agent without a formal amendment.
- **Decision authority** — who approves architectural changes, who can amend the constitution, how amendments are made (from Q28–Q29)
- **Constitution index** — table of every generated file, its one-line purpose, and path
- **Key decisions log** — table of 5–10 most significant decisions made during the interview, with one-line rationale for each (record *why*, not just *what*)
- **Amendment history** — initial entry with creation date, author, and "founding version" note

## Example Structure

```markdown
# [Project Name] — Project Constitution
> Version 1.0 | Created [date] | Status: Active

## Immutable Principles
These rules may not be overridden by any team member, process, or AI agent without a formal constitution amendment.

1. [Principle — e.g., "No service may directly access another service's database."]
2. [Principle — e.g., "All external API changes require a versioned deprecation period of 90 days."]
3. [Principle — e.g., "No secrets may exist in source code or Docker images under any circumstances."]

## Decision Authority
- Architectural changes: [from Q28]
- Constitution amendments: [from Q29]

## Constitution Index
| Document | Purpose | Path |
|----------|---------|------|
| Architecture | System topology and service boundaries | ai-context/architecture.md |
| Tech Stack | Canonical technology choices | ai-context/tech-stack.md |
| Coding Standards | Language conventions and review standards | ai-context/coding-standards.md |
| Testing | Test strategy and coverage requirements | ai-context/testing.md |
| Database Guidelines | DB conventions, naming, migrations, auditing | ai-context/database-guidelines.md |
| ... | ... | ... |

## Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary language | TypeScript (strict) | Team fluency; type safety at scale |
| Auth model | OAuth 2.0 via Google SSO | No password storage; enterprise SSO requirement |
| ... | ... | ... |

## Amendment History
| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0 | [date] | [author] | Initial constitution — greenfield project setup |
```
