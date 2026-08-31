# CLI composition

The CLI registers the public command families and routes them through typed,
dependency-injected adapters. The installed `open-brain` process loads one explicit
application configuration and binds all 17 families to confined local services. Building
the composition starts no listener, scheduler, provider, or network operation. Selected
commands receive only the capabilities they need.

This is synthetic implementation readiness. It is not a claim of live parity, cutover,
or service health.

## Service processes

`open-brain-mcp` runs the work-only stdio MCP server. It needs the normal retained-root
configuration, but it does not require the HTTP credential. Its tool set is limited to
`brain_query` and metadata-only `brain_retrieval_feedback`.

`open-brain-http` runs the bounded UI/share server. It requires exactly one named
`service_token` secret reference in configuration. The secret is resolved only during
HTTP composition and is never placed in a result or retained in application metadata.
The listener defaults to `127.0.0.1:8788`; a private-network bind requires explicit
non-secret bind configuration and still rejects public or wildcard addresses.

## Commands

`capture`, `config`, `cron`, `digest`, `doctor`, `explain`, `ledger`, `migrate`, `okf`, `proposals`, `query`, `registry`, `retention`, `review`, `share`, `social`, and `status` are registered in lexical order.

An injected adapter receives the exact arguments after its command family. Adapter output
must name the selected family, include a status, be JSON-safe, and pass the public-output
redaction checks. A missing adapter returns `command_adapter_unavailable`. An exception,
malformed result, mismatched command, echoed argument, credential-like value, URL, path,
traceback, or exception residual returns `command_adapter_failed`. Neither response
includes the rejected value.

Ordinary family adapters cannot emit live, parity, or cutover readiness fields at any
nesting level. Public strings and field names are checked through at most three rounds of
percent-decoding; output that has not converged at that bound is rejected without residue.

`migrate state-backfill` and `migrate processed-at-backfill` expose redacted,
non-mutating plans. Production does not infer an Obsidian layout taxonomy, so
`migrate content-layout` is rejected unless a caller uses the separately configured typed
migration API. Apply and restore stay behind receipt-bound backup and recovery authority;
the public CLI does not turn a plan into ambient mutation authority.

`review edit` and `review archive` dispatch through a root-confined SQLite maintenance store.
The edit contract uses the exact predecessor category taxonomy and domain aliases, preserves
an omitted title or classification class, supports confined nested slugs, keeps the review open,
and rejects privacy widening. Archive accepts a strict `YYYY-MM` cutoff, moves only older applied
or rejected reviews, preserves the active store on dry-run, and records hash-bound maintenance
events. The process composition root opens this store only after the `review` family is selected.

## Output and exits

Use `--json` for a deterministic JSON envelope. Use `--dry-run` to request
non-mutating behavior from a write adapter. These flags are accepted before or after the
command name and are forwarded in the exact remaining argument tuple.

| Exit | Class | Meaning |
| --- | --- | --- |
| 0 | success | No command was requested, or help/version was requested. |
| 1 | failure | Adapter unavailable, failed, or returned unsafe/invalid output. |
| 2 | usage | The command or its arguments are invalid. |
| 3 | deferred | A review decision was explicitly deferred; this is not an unimplemented capability. |

Error envelopes include only a stable error code, a generic message, and
`redacted: true`. Exception text, configuration values, paths, credentials, URLs, and
input arguments are not emitted.
