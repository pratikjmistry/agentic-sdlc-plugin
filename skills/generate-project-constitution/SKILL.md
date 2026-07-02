---
name: generate-project-constitution
description: >
  Use this skill when the user types /generate-project-constitution or wants to establish engineering
  standards and architectural guardrails before decomposing features.
  Trigger on: "/generate-project-constitution", "generate project constitution",
  "create architecture docs", "define project standards", "set up project guidelines",
  "create coding standards", "define tech stack", "set engineering conventions",
  "generate ai-context files", "create architecture.md", "define project guardrails",
  "we approved the PRD, now set up the project standards",
  "before we break into features, let's define our conventions",
  or any request to establish project-level engineering standards before development begins.
  Step 2.5 of the Greenfield workflow: /grill → /write-prd → [/generate-project-constitution]
  → /prd-to-features → HITL Feature Review → /feature-to-issues → Ready to Develop.
---

# /generate-project-constitution — Project Constitution Generator

## Workflow Role

`/generate-project-constitution` is **Step 2.5 of the Greenfield workflow** — inserted between PRD approval and feature decomposition.

```
GREENFIELD:
  /grill → /write-prd → [/generate-project-constitution] → /prd-to-features → HITL Feature Review
                                                                              → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**Input:** An approved PRD (from `/write-prd`, HITL Checkpoint passed) and answers to a structured interview.
**Output:** A set of Markdown constitution files saved to `/ai-context/`, consumed by `/prd-to-features`, `/feature-to-issues`, and all downstream engineering steps.

---

## Purpose

A Project Constitution is a set of authoritative, project-specific reference documents that encode architectural decisions, engineering standards, and team conventions *before* any feature is decomposed or issue is created. It gives every downstream AI and human the same shared understanding of how this project is built, deployed, and maintained.

Without a constitution, features get decomposed against a blank canvas. With one, every feature inherits real constraints: the right tech stack, the right security model, the right testing approach — all without repeating them in every issue.

---

## What the Constitution Is (and Isn't)

**IS:** Authoritative project-level decisions. Specific, opinionated, and tailored to this project.

**IS NOT:** Generic boilerplate. Aspirational ("we aim to…"). Copied from templates without customisation.

Every sentence in a constitution file should be something an engineer could act on or a reviewer could check. If it couldn't fail a code review, it shouldn't be in the constitution.

---

## Constitution Files

The following files may be generated. Not all apply to every project. The interview determines which ones are needed.

| File | Content Summary | Always? |
|------|----------------|---------|
| `project-constitution.md` | Master governance document: immutable principles, decision authority, and index of all detailed docs | **Yes — always** |
| `architecture.md` | System topology, service boundaries, data ownership, integration patterns | Yes |
| `tech-stack.md` | Canonical technology choices per layer, with rationale and constraints | Yes |
| `coding-standards.md` | Language conventions, formatting, linting, naming, review expectations | Yes |
| `testing.md` | Testing strategy, coverage requirements, tooling, E2E scope | Yes |
| `security.md` | Auth model, data classification, secrets management, threat model | If public-facing, has auth, or compliance required |
| `api-guidelines.md` | API style (REST/GraphQL/etc.), versioning, error formats, rate limiting | If external API consumers or multiple services |
| `design-system.md` | Component library, token system, responsive strategy, accessibility baseline | If significant frontend/UI work |
| `deployment.md` | Environment model, CI/CD pipeline, infrastructure-as-code conventions, rollback | If cloud, containers, or automated deployment |
| `observability.md` | Logging standards, tracing, metrics, alerting thresholds, dashboards | If production service, microservices, or compliance |
| `repo-structure.md` | Monorepo/polyrepo layout, module conventions, dependency rules | If multi-service, monorepo, or team > 5 |
| `database-guidelines.md` | DB technology choice, naming conventions, ID strategy, migration tooling, auditing, indexing, ORM guidance, multi-tenancy model, soft-delete strategy | If any persistent data store is used |
| `ralph-agent-spec.md` | Agent loop definitions for Ralph-impl, Ralph-test, and Ralph-e2e — responsibilities, inputs/outputs, completion contract, and handover model | If using agentic coding loop (Claude Code / Ralph) |

`project-constitution.md` is the entry point to the entire constitution. It is always generated, regardless of project scope, and always generated last — after the detailed files — so it can accurately reference them.

All files are saved to `/ai-context/` so they are automatically available to `/write-prd` and all downstream skills.

---

## Execution Protocol

### Step 0 — Load PRD Context

If an approved PRD is provided, read it silently and extract:
- Project name and type
- Technology signals (any stack mentions)
- Deployment or infrastructure signals
- Team or persona signals
- Compliance or security signals

Use this to pre-fill sensible defaults and skip obvious questions. Do not ask what the PRD already tells you.

---

### Step 1 — Run the Structured Interview

The interview is **adaptive and open-ended** — there is no fixed number of rounds. Continue asking questions until you have enough information to make confident, specific decisions about every applicable constitution file. Shallow answers lead to generic files; the interview is what makes the difference.

Use the `AskUserQuestion` tool wherever possible so the user can select from options. Group related questions into a single call (up to 4 per call) to avoid one-question-at-a-time friction. After each batch, assess what gaps remain and ask the next most important batch. Stop when you have what you need — not before.

**What "enough information" means:** you should be able to name the actual tech, version, auth model, deployment target, team structure, and compliance constraints before writing a single file. If any of those are still vague or marked `[DECISION PENDING]`, you haven't asked enough.

---

#### Phase 1 — System Shape

These questions determine which files to generate and set the scope for everything else. Ask them first.

**Q1. System type** — What is the primary nature of this system?
- Full-stack web application (frontend + backend)
- API / backend service only (no UI)
- Mobile application (iOS, Android, or cross-platform)
- Data pipeline or batch processing system
- CLI tool or developer tooling
- Multi-service / microservices platform
- Other (describe)

**Q2. Frontend / UI** — Does this project include user-facing UI?
- Yes — significant UI with a component library or design system
- Yes — lightweight UI, no design system needed
- No — API or backend only

**Q3. API surface** — Who consumes the APIs this system exposes?
- External third parties (public API, partner integrations)
- Other internal teams or services
- Only the frontend we own
- No APIs exposed externally

**Q4. Deployment target** — Where does this system run?
- Cloud managed services (AWS, GCP, Azure — with IaC/Terraform)
- Containers / Kubernetes
- Serverless (Lambda, Cloud Functions, etc.)
- On-premises / self-hosted
- npm / package registry / local distribution
- Not yet decided / early stage

**Q_INT. Integration layer** — What does "wiring a feature together" look like in this project? The INT layer in issue decomposition is the step that assembles all the atomic pieces (data layer, service layer, UI layer) into a working, end-to-end flow. Describe what that means here in one sentence.

(This answer goes into `ai-context/architecture.md` as the **Integration Layer Definition** and is used by `/feature-to-issues` and Ralph-impl to scope and validate INT issues correctly.)

Examples by project type:
- Web app: "Registering components in the router and wiring them to API clients so the feature is reachable and functional in the running app"
- Mobile app: "Adding the feature screen to the navigation stack and connecting it to the data layer so it is reachable and functional in the simulator"
- Data pipeline: "Connecting pipeline stages in the orchestrator so data flows end-to-end from source to sink"
- API platform: "Registering the service in the API gateway and wiring cross-service calls so the feature is reachable from the public surface"
- Backend service: "Wiring the new endpoints into the router and connecting all middleware, auth, and service dependencies so the feature is reachable and functional"
- CLI tool: "Registering the new command in the CLI entry point and wiring subcommands, options, and output handlers"

---

#### Phase 2 — Team, Compliance, and Codebase

**Q5. Team size** — How large is the engineering team?
- Solo / 1-2 engineers
- Small team (3–8 engineers)
- Medium team (9–25 engineers)
- Large / multi-team (25+ engineers)

**Q6. Compliance requirements** — Are there any regulatory or compliance requirements?
- None
- GDPR / data privacy
- HIPAA
- SOC 2
- PCI-DSS
- Multiple (describe)

**Q7. Service structure** — How is the codebase organised?
- Single repository, single service (monolith)
- Single repository, multiple services (monorepo)
- Multiple repositories, multiple services (polyrepo)
- Not yet decided

**Q8. Existing conventions** — Are there existing coding standards or conventions to inherit?
- Yes — I'll describe them
- Partially — some conventions exist, fill the gaps
- No — greenfield, establish everything from scratch

---

#### Phase 3 — Technology Decisions

Ask these regardless of whether the PRD mentions technology. Specific versions and explicit rationale are what separate a useful constitution from a generic one.

**Q9. Backend language and framework** — What language and framework does the backend use?
(Free text — or offer common options: Node/Express, Node/Fastify, Python/FastAPI, Python/Django, .NET Core, Go/Gin, Java/Spring, Ruby/Rails, other)

**Q10. Frontend framework** — (Skip if no UI) What frontend framework and build tooling?
(Free text — or offer: React+Vite, React+Next.js, Vue+Vite, Angular, Svelte, other)

**Q11. Database and caching** — What are the primary data stores?
(Free text — prompt for: primary DB, secondary DB if any, cache layer, search index if applicable)

**If any database is used (ask after Q11):**

**Q11a. ID strategy** — How are primary keys generated?
- Auto-increment integers
- UUIDs (v4 random)
- UUIDs (v7 time-ordered — recommended for indexed tables)
- Application-generated (CUID, NanoID, etc.)
- Mixed (describe per entity type)

**Q11b. Migration tooling** — How are database migrations managed?
(Free text — or offer: Flyway, Liquibase, EF Core Migrations, Alembic, Prisma Migrate, Knex, raw SQL scripts, not yet decided)

**Q11c. Auditing approach** — How are data changes tracked?
- `created_at` / `updated_at` timestamps only
- Soft-delete with `deleted_at` column
- Full audit table (separate table logging all mutations with user + timestamp)
- Event sourcing
- No auditing required

**Q11d. Multi-tenancy model** — How is tenant data isolated (skip if single-tenant)?
- Row-level (tenant_id column on every table)
- Schema-per-tenant (separate DB schema per tenant)
- Database-per-tenant (separate DB instance per tenant)
- Not applicable — single tenant

**Q11e. ORM / query layer** — What ORM or query builder is used?
(Free text — or offer: Prisma, TypeORM, Sequelize, SQLAlchemy, Entity Framework, Hibernate, JOOQ, raw SQL, not yet decided)

**Q12. Infrastructure and IaC** — What is the infrastructure tooling?
(Free text — or offer: Terraform, Pulumi, CDK, Helm, Ansible, none/manual, not decided)

**Q13. Unit test framework** — What framework is used for unit and integration tests?
(Free text — or offer: Jest, Vitest, pytest, NUnit, xUnit, JUnit, RSpec, Go test, other, not decided)

**Q14. E2E test tool** — What tool is used for end-to-end and browser automation tests?
- Playwright (recommended)
- Cypress
- Selenium / WebDriver
- No E2E tests planned
- Not yet decided

**Q15. Code coverage** — What is the minimum acceptable code coverage threshold, and does it block CI?
(Free text — e.g. "80% line coverage, blocks merge"; "no enforced threshold"; "not yet decided")

**Q16. CI test gate** — Which test types must pass before a PR can be merged?
(Multiselect — Unit tests, Integration tests, E2E tests, Linting/type-check, Coverage threshold)

**Q17. Test environment strategy** — Where do integration tests run?
- Local docker-compose (no external deps)
- Ephemeral per-PR environment (spun up in CI)
- Shared dev/staging environment
- Against mocked services only
- Not yet decided

---

#### Phase 4 — Domain-Specific Deep Dives

Ask only the questions relevant to this project based on Phase 1–3 answers. Skip questions that don't apply.

**If public-facing OR has auth OR compliance flagged:**

**Q13. Authentication model** — How are users or services authenticated?
- JWT (access + refresh tokens)
- OAuth 2.0 / OIDC (SSO via Google, Microsoft, etc.)
- API keys
- Session-based (server-side sessions)
- mTLS (service-to-service)
- Multiple (describe)

**Q14. Authorisation model** — How are permissions controlled?
- Role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Simple ownership (users only see their own data)
- No auth required
- Not yet defined

**Q15. Data classification** — What categories of sensitive data does the system handle?
(Multiselect: PII — names/emails/addresses, Financial data, Health data, Authentication credentials, Internal-only business data, No sensitive data)

**If compliance was flagged (HIPAA / SOC 2 / PCI-DSS / GDPR):**

**Q16. Audit logging** — What events must be logged for compliance?
(Free text — prompt for: user authentication events, data access, data modification, admin actions, retention period)

**Q17. Data residency** — Are there data residency or geographic restrictions?
- No restrictions
- EU only (GDPR)
- US only
- Specific regions (describe)

**If multi-service OR microservices:**

**Q18. Inter-service communication** — How do services talk to each other?
- Synchronous REST
- Synchronous gRPC
- Asynchronous events / message queue (Kafka, RabbitMQ, SQS)
- Mixed (describe which services use which)

**Q19. Service discovery and routing** — How are services found and routed?
(Free text — or offer: API Gateway, service mesh/Istio, internal DNS, load balancer, Kubernetes services)

**If significant frontend / design system:**

**Q20. Component library** — What UI component library or design system is in use?
(Free text — or offer: shadcn/ui, MUI, Ant Design, Chakra UI, custom, none yet)

**Q21. Accessibility target** — What accessibility standard must the UI meet?
- WCAG 2.1 AA (recommended baseline)
- WCAG 2.1 AAA
- WCAG 2.2 AA
- No formal target yet

**If cloud / containers / serverless deployment:**

**Q22. Environment model** — How many deployment environments exist and what are they?
(Free text — prompt for: names of envs, what differs between them, who can deploy to each)

**Q23. Deployment strategy** — How are releases deployed?
- Blue/green deployment
- Canary (gradual traffic shift)
- Rolling update
- Direct / in-place (acceptable for non-production)
- Not yet decided

**Q24. Secrets management** — Where do secrets and config live?
(Free text — or offer: AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, Kubernetes Secrets, environment variables in CI, not yet decided)

**If team > 5 OR monorepo OR polyrepo:**

**Q25. Branch strategy** — What is the branching and release model?
- Trunk-based development (short-lived feature branches → main)
- Gitflow (feature → develop → release → main)
- Environment branches (main → staging → production)
- Not yet decided

**Q26. PR and review standards** — What are the review requirements?
(Free text — prompt for: minimum reviewers, who can approve, what triggers auto-checks)

---

#### Phase 5 — Immutable Principles (always ask)

These answers directly populate `project-constitution.md`. Don't skip them.

**Q27. What are the 3–5 non-negotiable principles that must never be violated in this project?**
(Free text — examples: "No direct database access from the frontend", "All external APIs must be versioned", "No secrets in source code", "Every change must have a test", "Backward compatibility must never be broken without a deprecation period")

**Q28. Who has final decision authority for architectural changes?**
(Free text — examples: "Tech Lead", "Architecture Review Board", "Any senior engineer via PR consensus", "CTO sign-off required")

**Q29. How should the constitution itself be amended?**
(Free text — or offer: PR with Tech Lead approval, Architecture Review Board vote, Any senior engineer, No formal process yet)

---

#### When to Stop

After each phase, assess: *can I write every applicable constitution file with specific, actionable content right now?* If yes, proceed to Step 2. If any file would still need placeholders or guesses for core decisions, ask another targeted batch.

It's better to ask one extra round than to generate a file full of `[DECISION PENDING]` entries.

---

### Step 2 — Recommend Constitution Files

Based on the interview answers, present the recommended file set to the user before generating anything:

```
Based on your answers, I recommend generating the following constitution files:

ALWAYS INCLUDED:
  ✅ project-constitution.md — master governance doc, immutable principles, index (generated last)
  ✅ architecture.md         — system topology and service design
  ✅ tech-stack.md           — canonical technology choices
  ✅ coding-standards.md     — language conventions and review standards
  ✅ testing.md              — test strategy and coverage expectations

RECOMMENDED FOR YOUR PROJECT:
  ✅ security.md         — [reason: public-facing system with auth requirements]
  ✅ deployment.md       — [reason: cloud/container deployment target]
  ✅ observability.md    — [reason: production microservices]

NOT NEEDED FOR THIS PROJECT:
  ⬜ design-system.md    — [reason: API-only, no frontend]
  ⬜ api-guidelines.md   — [reason: internal consumers only, patterns covered in architecture.md]
  ⬜ repo-structure.md   — [reason: single service monolith]

Shall I proceed with these files, or do you want to add or remove any?
```

Wait for the user to confirm or adjust the file list before generating.

---

### Step 3 — Generate Constitution Files

Generate each confirmed file. Each file must be:

- **Project-specific** — use the actual project name, stack, and decisions from the interview
- **Actionable** — every statement is something an engineer can act on or a tool can verify
- **Non-redundant** — don't repeat the same information across multiple files; cross-reference instead
- **Decision-recording** — for non-obvious choices, include a brief rationale so future engineers understand why

#### Phase 1 — Load Templates (parent context)

Before spawning agents, load every template for confirmed files. Find the skill directory from the `<location>` tag in the `<available_skills>` section of your system prompt (e.g. `.../skills/generate-project-constitution/SKILL.md`) and replace `SKILL.md` with `templates/<filename>.md`. Use `Read` to load each template. Do **not** load templates for skipped files.

Available templates (in `templates/` subdirectory alongside this SKILL.md):

| File | Template |
|------|---------|
| `architecture.md` | `templates/architecture.md` |
| `tech-stack.md` | `templates/tech-stack.md` |
| `coding-standards.md` | `templates/coding-standards.md` |
| `testing.md` | `templates/testing.md` |
| `security.md` | `templates/security.md` |
| `api-guidelines.md` | `templates/api-guidelines.md` |
| `design-system.md` | `templates/design-system.md` |
| `deployment.md` | `templates/deployment.md` |
| `observability.md` | `templates/observability.md` |
| `repo-structure.md` | `templates/repo-structure.md` |
| `database-guidelines.md` | `templates/database-guidelines.md` |
| `ralph-agent-spec.md` | `templates/ralph-agent-spec.md` |
| `project-constitution.md` | `templates/project-constitution.md` — load last, after all other files confirmed |

#### Phase 2 — Parallel Constitution File Generation

**Spawn one Agent per confirmed file** (except `project-constitution.md`) **in a single response** so they run in parallel. Each agent is self-contained — it cannot read the parent conversation.

Use this prompt template for each agent (fill in all placeholders):

---
```
You are generating a single project constitution file. Use the Write tool to save it and return one confirmation line.

Project folder (absolute path): [PROJECT_FOLDER]
Output file: ai-context/[FILENAME].md
Project name: [PROJECT_NAME]

Relevant interview answers for this file:
[PASTE ONLY THE Q&A ANSWERS RELEVANT TO THIS SPECIFIC FILE — not the full interview]

Template — required sections and example structure:
[PASTE THE FULL CONTENT OF templates/FILENAME.md AS READ IN PHASE 1]

Generate a complete, project-specific ai-context/[FILENAME].md. Every statement must be actionable and specific to this project. No placeholders, no generic advice. Cross-reference other constitution files by path (e.g. "see ai-context/security.md") rather than repeating content.

Use the Write tool to save the file. Reply with exactly: "✅ ai-context/[FILENAME].md"
```
---

Wait for all agent confirmations before proceeding.

#### Phase 3 — Generate project-constitution.md (parent context)

After all parallel agents confirm, read `templates/project-constitution.md`, then generate `ai-context/project-constitution.md` in the parent context. This file references all the files just written, so it must be generated last.
---

### Step 4 — Confirm and Checkpoint

After all agents have confirmed and `project-constitution.md` has been written, output a summary:

```
✅ Project Constitution Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: [Name]
Files generated: [N]

  /ai-context/project-constitution.md  ← start here
  /ai-context/architecture.md
  /ai-context/tech-stack.md
  /ai-context/coding-standards.md
  /ai-context/testing.md
  /ai-context/database-guidelines.md  (if any data store used)
  [additional files...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HITL CHECKPOINT — Constitution Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the `AskUserQuestion` tool to interactively collect confirmation before proceeding. Present a **multi-select** question so the user confirms all items in a single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the Project Constitution review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. Technology choices accurately reflect project decisions
  2. Architecture matches intended system design
  3. Security model covers all applicable threats
  4. Testing strategy meets quality expectations
  5. No contradictions between constitution files

**If all 5 items are selected:** State "✅ Constitution Approved." Then instruct the user to run `/prd-to-features`.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ Constitution requires revision — update the relevant files before proceeding.", and halt.
        ☐ Requires Revision — update files before proceeding

Next step: /prd-to-features
```

---

## File Recommendation Logic (Quick Reference)

Use this to guide recommendations when answers are nuanced:

```
security.md    → include if: public-facing OR has auth OR has compliance OR handles PII
api-guidelines → include if: external API consumers OR multiple internal services OR GraphQL
design-system  → include if: frontend with component library OR design tokens in use
deployment.md  → include if: cloud OR containers OR serverless OR CI/CD pipeline exists
observability  → include if: production system OR microservices OR compliance (audit logging)
repo-structure → include if: monorepo OR polyrepo OR team ≥ 9 OR multiple services
```

When in doubt, **include** the file. A thin file with 3 real decisions is better than a missing file that forces downstream agents to guess.

---

## Quality Guardrails

### NEVER generate:
- Generic boilerplate that doesn't reflect this project's actual decisions
- Aspirational statements without actionable implementation ("we will strive to…")
- Contradictions between files (e.g., security.md says JWT, tech-stack.md says sessions)
- Files that duplicate each other without cross-referencing
- Vague standards ("code should be clean", "tests should be comprehensive")

### ALWAYS:
- Use the actual project name, team size, and tech choices from the interview
- Cross-reference between files rather than duplicating content
- Record the rationale for non-obvious decisions in 1 line
- Flag open decisions explicitly: mark as `[DECISION PENDING]` rather than guessing
- Confirm the file list with the user before generating

---

## Examples of Good vs. Bad Constitution Statements

**coding-standards.md:**
❌ "Code should be clean and easy to read."
✅ "All TypeScript files use `prettier` (v3.x) with the config at `.prettierrc`. Max line length: 100. Single quotes. No semicolons. Violations block CI."

**security.md:**
❌ "The system should be secure."
✅ "All API endpoints require a valid JWT signed with RS256. Token lifetime is 15 minutes. Refresh tokens are httpOnly cookies with 7-day expiry and rotation on use."

**testing.md:**
❌ "We should have good test coverage."
✅ "Unit test coverage threshold: 80% (enforced by Jest `--coverage` in CI). E2E tests cover the 5 core user flows defined in Playwright suite. Tests in `/e2e/critical/` are required to pass before any PR merges to `main`."

**tech-stack.md:**
❌ "We use React for frontend and Node for backend."
✅ "Frontend: React 18 with TypeScript 5. State: Zustand (no Redux — we chose Zustand for its minimal boilerplate given team size). Build: Vite. Backend: Node 20 LTS, Express 5. ORM: Prisma (chosen for type safety and migration tooling). Database: PostgreSQL 16."
