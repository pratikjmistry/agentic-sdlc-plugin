# Template: design-system.md

## Required Sections

- **Component library** — name and version in use, or "custom" with location
- **Design token structure** — colour, spacing, typography tokens; where they live; how to add new ones
- **Responsive strategy** — breakpoints, mobile-first vs. desktop-first, fluid vs. fixed
- **Accessibility baseline** — WCAG level (2.1 AA recommended), keyboard nav requirements, screen reader testing approach
- **New component creation process** — when to add a new component vs. composing existing ones; who reviews
- **Enforcement** — name the specific automated check that verifies every rule above in CI and blocks merge
  on violation (e.g. an accessibility scanner such as axe-core wired into the test suite, a design-token lint
  rule, a visual-regression check). A rule in this document that no tool checks is a suggestion, not a
  standard — do not write a rule here without also naming what enforces it. If no automated check exists yet,
  write `[DECISION PENDING — enforcement mechanism not yet defined]` rather than omitting this section.
