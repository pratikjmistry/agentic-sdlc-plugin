# Template: deployment.md

## Required Sections

- **Environment model** — names of all environments (dev, staging, prod, etc.), what differs between them, who can deploy to each
- **CI/CD pipeline overview** — trigger conditions, stages, gates that block promotion
- **Infrastructure-as-code approach** — tool (Terraform, Pulumi, CDK, Helm), where IaC lives, how it's applied
- **Deployment strategy** — blue/green, canary, rolling, or in-place; rationale for the choice
- **Rollback procedure** — how to revert a bad deployment; automated vs. manual; time target
- **Environment-specific configuration management** — how config/secrets differ per env; no hardcoded env-specific values in code
