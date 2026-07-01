# Greenfield Workflow Plugin

End-to-end planning workflow for new software projects — from raw idea to structured, platform-ready issues — with a full TDD test plan and project constitution built in.

## Workflow

```
/grill                        → Interrogate and clarify the idea
/write-prd                    → Generate structured PRD with FRs, ACs, Playwright scenarios
/generate-project-constitution → Interview and generate /ai-context/ architecture files
/prd-to-features              → Decompose PRD into Features and User Stories
  ↓ HITL Feature Review
/write-test-plan              → Generate TDD test plan (UT-, IT-, ST-, RT-) from requirements
  ↓ HITL Test Plan Review
/feature-to-issues            → Decompose features into atomic, dependency-ordered issues
  ↓ HITL Issue Review
/push-to-pms                  → Create issues in GitHub, GitLab, Azure DevOps, Jira, or Linear
  ↓ Ready to Develop (hand off to Claude Code)
```

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| Grill | `/grill` | Interrogates vague ideas into clear requirements |
| Write PRD | `/write-prd` | Produces implementation-ready Product Requirements Document |
| Generate Project Constitution | `/generate-project-constitution` | Interviews and generates `/ai-context/` architecture files |
| PRD to Features | `/prd-to-features` | Decomposes PRD into Features with User Stories |
| Write Feature | `/write-feature` | Brownfield path — structures a single feature without a PRD |
| Write Test Plan | `/write-test-plan` | Generates TDD test plan from FRs and ACs |
| Feature to Issues | `/feature-to-issues` | Decomposes features into atomic issues with dependency graph |
| Push to PMS | `/push-to-pms` | Creates issues in your chosen project management platform |

## Output Files

All planning artifacts are saved to `/ai-context/` in your project repository:

| File | Produced By |
|------|------------|
| `architecture.md` | `/generate-project-constitution` |
| `tech-stack.md` | `/generate-project-constitution` |
| `coding-standards.md` | `/generate-project-constitution` |
| `testing.md` | `/generate-project-constitution` |
| `security.md` | `/generate-project-constitution` (if applicable) |
| `project-constitution.md` | `/generate-project-constitution` |
| `test-plan.md` | `/write-test-plan` |
| `issues.json` | `/feature-to-issues` |
| `pms-map.json` | `/push-to-pms` |

These files are consumed by Claude Code during development as project context.

## Connectors

See `CONNECTORS.md` for setup instructions. Only needed for `/push-to-pms`.

## HITL Checkpoints

Each major step ends with a Human-in-the-Loop review checkpoint. Do not proceed to the next step until you have explicitly confirmed the output.
