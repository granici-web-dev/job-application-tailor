# STACK.md — Job Application Tailor

Locked technology choices, taken from SPEC.md §5. The anti-choices matter as much as the choices: they exist to prevent drift.

## Backend (Python 3.11+)

| Concern | Choice | Why |
|---|---|---|
| HTTP API | `fastapi` + `uvicorn` | Typed request/response models, async, minimal ceremony for a small local API. |
| LLM | `anthropic` | Job analysis, CV tailoring, cover-letter generation. Model set in config, defaults to a current Claude model. |
| Fetch | `requests` + `beautifulsoup4` | Download job HTML, strip scripts/styles/nav, extract main text. |
| PDF | `weasyprint` + `markdown` | Markdown to HTML to ATS-compatible PDF with selectable text. |
| Excel | `openpyxl` | The shared `applications_tracker.xlsx`, including the status dropdown via `DataValidation`. |
| Config | `python-dotenv` | `ANTHROPIC_API_KEY` from `.env`. |

## Frontend (Node 20)

| Concern | Choice | Why |
|---|---|---|
| Build / dev | `vite` | Fast dev server with reliable HMR (needed for impeccable Live Mode + agentation). |
| UI | `react` + `typescript` | Small SPA: URL input, generate button, result card, PDF preview iframe, history table, status toggle. |
| API access | REST to the FastAPI backend | Endpoints per SPEC §7. CORS open for the local Vite origin only. |

## Runtime

- **Docker Compose** runs backend (`:8000`) and frontend (`:5173`). The host only needs Docker, plus Node for the Claude Code dev tooling. CLI runs via `docker compose run --rm backend python -m backend.apply "<URL>"`.

## Decisions and anti-choices

- **No database.** Output is files on disk: per-company folders of PDFs plus one shared Excel tracker. The filesystem is the store. Adding a DB would be solving a problem we don't have.
- **No ORM.** Follows from no database.
- **Playwright is deferred, behind a flag.** Plain `requests` + `beautifulsoup4` is the default fetch path. JS-rendered pages get a manual-paste fallback (`--text-file`) before we reach for a headless browser. Add Playwright only when manual paste proves too painful, and keep it opt-in.
- **Never bypass bot protection.** No captcha-solving, no anti-bot evasion. When a page won't yield its text, the tool tells the user and accepts pasted text instead.
- **The dev tools are not app dependencies.** rigorous, impeccable, and agentation are Claude Code tooling. They never enter `requirements.txt` or `package.json`.
- **App dependencies are exactly the list above.** Adding a runtime dependency is a deliberate decision, not a reflex. Prefer the standard library and what's already pinned.
