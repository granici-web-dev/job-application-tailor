# TESTING.md — Job Application Tailor

What's worth testing here, what isn't, and how. Tests exist to protect the things that would silently corrupt a job application; they are not a coverage-number ritual.

## What's worth testing

- **Pure logic and utilities.** Filename/folder sanitization (illegal chars, spaces, collision suffixes), document-language detection, LLM JSON parsing (stripping ```json fences, handling malformed output), and the Excel row builder. Fast, deterministic, highest value.
- **Pipeline orchestration.** The end-to-end `pipeline.py` flow with the Anthropic client and network fetch mocked. Verifies the steps wire together: analysis feeds tailoring, outputs land in the right `output/<Company>/` folder, the tracker gets exactly one appended row.
- **API endpoints.** FastAPI routes via the test client: `POST /generate` happy path, `PATCH /applications/{id}/status` actually syncs back to the Excel file, `GET /files/...` serves the right artifact.
- **Deterministic PDF / output properties.** Not the model's wording. We assert the checkable, stable facts: the rendered PDF contains selectable text (not an image), is single-column, and the prompt-assembly never injects skills absent from `master_cv.md`. The "no fabrication" guardrail is a test target.

## What's not worth testing

- Exact LLM-generated copy. It's non-deterministic and would rot; asserting on it produces brittle, rubber-stamped tests.
- Third-party libraries (WeasyPrint internals, openpyxl, the Anthropic SDK). We test our use of them, not them.
- Trivial glue: passthrough getters, framework wiring, config loading with no logic.

## Mocking policy

- **Mock externals, use real local I/O.** Stub the Anthropic client and HTTP fetch so tests are fast and offline. Use the real filesystem (via tmp dirs) and the real `openpyxl` / `weasyprint` so we test actual artifacts, not mock call assertions.
- Anthropic responses are mocked with realistic fixtures (valid JSON, and deliberately malformed JSON to exercise the retry-once path from SPEC §8).

## Coverage and speed

- **Covered where it matters.** No coverage percentage to chase. Cover the logic whose failure would silently ship a wrong CV or break the tracker; skip the glue.
- The suite should stay fast enough to run on every change. A single test that renders a real PDF is acceptable; a suite that calls the live API is not.

## Snapshots

- **Sparingly, structured output only.** A golden snapshot is fine for stable structured output: the Excel header row, column order, the status dropdown formula, a deterministic rendered HTML template. Never snapshot LLM-generated text.

## Layout and naming

- Tests live in `backend/tests/`, mirroring module names: `test_utils.py`, `test_analyze.py`, `test_tracker.py`, `test_pipeline.py`, `test_api.py`.
- Test names state the behavior: `test_company_folder_name_strips_illegal_characters`, `test_tracker_appends_row_without_overwriting`, `test_analyze_retries_once_on_invalid_json`.
- Fixtures (sample job HTML, mock Anthropic responses, a minimal `profile/`) live in `backend/tests/fixtures/` and are built by small factory helpers, not copy-pasted per test.
