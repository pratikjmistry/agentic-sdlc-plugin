# Template: observability.md

## Required Sections

- **Logging standard** — format (structured JSON recommended), required fields (timestamp, level, trace_id, service), log levels and when to use each
- **Distributed tracing** — tool (OpenTelemetry, Jaeger, Datadog APM, etc.), sampling strategy
- **Metrics** — what is instrumented (RED: Rate, Errors, Duration), naming convention for metric names
- **Alerting thresholds** — for critical paths: latency p99, error rate, saturation
- **On-call runbook location or convention** — where runbooks live, format, update ownership
- **SLI/SLO targets** — availability, latency, error budget; or mark as "TBD — define after launch"
