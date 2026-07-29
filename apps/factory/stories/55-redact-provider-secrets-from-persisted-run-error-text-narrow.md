# Story

## Story
As a maintainer of runner persistence,
I want provider-secret substrings redacted from run error text before persistence,
so that transient provider failures cannot become durable secret exposure in `state/factory.db`.

## Acceptance Criteria
1. A pure helper redacts common provider-secret patterns from an arbitrary string — OpenAI/Anthropic `sk-...` and `sk-ant-...` tokens, `Bearer <token>` and `Authorization: ...` headers, and long key-like hex/base64 runs — replacing each occurrence with the literal `[REDACTED]`.
2. `factory.runner._record_run` applies the redactor to the `error` value before the run row is written, so no persisted run row can contain a raw secret.
3. The redactor is idempotent (re-redacting already-redacted text is a no-op) and leaves text that contains no secret pattern byte-for-byte unchanged.
4. Unit tests cover: a string containing an `sk-...` token is redacted; a `Bearer`/`Authorization` header value is redacted; a plain error message is unchanged; and the redaction is actually applied on the `_record_run` persistence path (a run recorded with a secret-bearing error stores `[REDACTED]`).

### Testable Claims (EARS)
AC1.1: WHEN the pure helper receives an arbitrary string containing an OpenAI or Anthropic `sk-...` or `sk-ant-...` token, THE helper SHALL replace each such occurrence with the literal `[REDACTED]`.
AC1.2: WHEN the pure helper receives an arbitrary string containing a `Bearer <token>` header value, THE helper SHALL replace each such occurrence with the literal `[REDACTED]`.
AC1.3: WHEN the pure helper receives an arbitrary string containing an `Authorization: ...` header value, THE helper SHALL replace each such occurrence with the literal `[REDACTED]`.
AC1.4: WHEN the pure helper receives an arbitrary string containing long key-like hex or base64 runs, THE helper SHALL replace each such occurrence with the literal `[REDACTED]`.
AC2.1: WHEN `factory.runner._record_run` writes a run row with an `error` value, THE runner SHALL apply the redactor to the `error` value before the row is written.
AC2.2: WHEN a run row is persisted from an `error` value containing a raw secret pattern, THE persisted run row SHALL not contain the raw secret in `error`.
AC3.1: WHEN the redactor is run on already-redacted text, THE redactor SHALL leave the text unchanged.
AC3.2: WHEN the redactor receives text containing no secret pattern, THE redactor SHALL leave the text byte-for-byte unchanged.
AC4.1: WHEN unit tests execute for a string containing an `sk-...` token, THE test suite SHALL verify that the string is redacted.
AC4.2: WHEN unit tests execute for a `Bearer` or `Authorization` header value, THE test suite SHALL verify that the header value is redacted.
AC4.3: WHEN unit tests execute for a plain error message, THE test suite SHALL verify that the message is unchanged.
AC4.4: WHEN unit tests execute for the `_record_run` persistence path with a secret-bearing error, THE test suite SHALL verify that the stored error contains `[REDACTED]` instead of the original secret-bearing substring.

## Tasks / Subtasks
- [ ] Identify runner persistence write path in `factory.runner._record_run`.
- [ ] Add pure redaction helper in backend code adjacent to runner persistence concerns.
- [ ] Implement pattern handling for `sk-...` tokens.
- [ ] Implement pattern handling for `sk-ant-...` tokens.
- [ ] Implement pattern handling for `Bearer <token>` values.
- [ ] Implement pattern handling for `Authorization: ...` values.
- [ ] Implement pattern handling for long key-like hex/base64 runs.
- [ ] Ensure replacement literal is exactly `[REDACTED]`.
- [ ] Ensure helper is idempotent on already-redacted text.
- [ ] Ensure helper preserves non-secret text byte-for-byte.
- [ ] Apply helper inside `_record_run` before DB insert/update of `error`.
- [ ] Add unit test for `sk-...` token redaction.
- [ ] Add unit test for `Bearer` header redaction.
- [ ] Add unit test for `Authorization:` header redaction.
- [ ] Add unit test for unchanged plain error text.
- [ ] Add unit test for idempotence.
- [ ] Add persistence-path unit test covering `_record_run` stored `error` redaction.
- [ ] Verify no test asserts on raw persisted secret text.

## Dev Notes
- No `flow.md` provided by direction.
- No `api_spec.md` provided by direction.
- No canonical context files were provided in the prelude (`context/project.md`, `context/navigation.md`, module files absent). Derive implementation targets from repository code at runtime.
- Scope note: narrow read covers the direction exactly as written; no expansion beyond run `error` persistence in `factory.runner._record_run`.
- Prefer a pure string-in/string-out helper so helper tests do not require DB setup.
- The persistence-path assertion must prove write-boundary sanitization, not only helper correctness.

### Direction Acceptance Criteria (verbatim)
- [ ] A pure helper redacts common provider-secret patterns from an arbitrary string — OpenAI/Anthropic `sk-...` and `sk-ant-...` tokens, `Bearer <token>` and `Authorization: ...` headers, and long key-like hex/base64 runs — replacing each occurrence with the literal `[REDACTED]`.
- [ ] `factory.runner._record_run` applies the redactor to the `error` value before the run row is written, so no persisted run row can contain a raw secret.
- [ ] The redactor is idempotent (re-redacting already-redacted text is a no-op) and leaves text that contains no secret pattern byte-for-byte unchanged.
- [ ] Unit tests cover: a string containing an `sk-...` token is redacted; a `Bearer`/`Authorization` header value is redacted; a plain error message is unchanged; and the redaction is actually applied on the `_record_run` persistence path (a run recorded with a secret-bearing error stores `[REDACTED]`).

## References
- Direction: `D005 redact provider secrets from persisted run error text`
- Persistence target: `factory.runner._record_run`
- Storage target named by direction: `state/factory.db`
- PM decomposition context: helper-first slice, then persistence-wire slice

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes: TBD

## Senior Developer Review
- Reviewer: TBD
- Outcome: Pending
- Notes: TBD

## Review Follow-ups
- None yet.
