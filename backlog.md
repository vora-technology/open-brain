# Backlog — Open Brain

**Last Updated:** 2026-08-26

Gate 1 implementation status after the governed production-replacement work.

## Bugs

None recorded.

## Features and enhancements

- [x] Add an immutable content-addressed derived-asset store before enabling downloaded-media capture success.
- [x] Select and verify a concrete staged model runtime against the image/text confinement matrix.
- [x] Add a production pinned HTTP transport and run the SSRF matrix against it.
- [x] Add the composition root and production HTTP server after transport and deployment contracts stabilize.
- [x] Add generic launchd/systemd templates after the service API stabilizes.
- [x] Add optional dependencies only after their ports are implemented. Cloud uses a locked optional SDK; MCP and the current integrations remain dependency-free.

## Tech debt

None recorded in the new implementation.

## Ideas and future work

- Container packaging after the Python service and deployment contract stabilize.
- Create a paid Vora Technology PyPI organization, approve the recurring per-member billing,
  register `open-brain` under that organization, and configure GitHub OIDC Trusted Publishing.
  This remains outside the public-repository-readiness goal and requires a separate billing gate.
