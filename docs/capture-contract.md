# Capture contract

The capture envelope preserves source, capture timestamp, normalized content type, immutable provenance, and the owner's one-line reason for saving an item.

Owner-authored captures require a non-empty one-line `capture_why`. Automated playlist captures may represent missing owner context explicitly as `automation_absent`; they are restricted to `hold` or `reference` and cannot become an idea or action candidate.

Intent is closed: `reference`, `idea`, `action_candidate`, or `hold`. Ideas and action candidates create review proposals only. Third-party content never silently creates a task.

Share intake accepts an owner-authored URL, reason, and optional shared text. Authentication, bounds, and JSON validation happen before durable queueing. Capture success requires immutable private raw persistence followed by either a durable private hold or receipt-bound event and distillation work. Capture creates no Markdown knowledge page or task.

Retries resume from durable boundaries. A capture with an existing extraction event retries only distillation queueing instead of fetching mutable source content again.
