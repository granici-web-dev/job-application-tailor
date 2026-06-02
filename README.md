# Job Application Tailor

Turn a job posting into a tailored, ATS-safe CV and cover letter — and track every application in one place.

You paste a link to a vacancy. The app reads the posting, tailors your master CV and a cover letter to that specific role (in the posting's own language), renders both as ATS-compatible PDFs, and logs the application in a spreadsheet you can manage from the web UI. Everything is grounded in your real experience — the tool is built so it **cannot** invent skills you don't have.

A full-stack project: FastAPI backend, React + TypeScript frontend, Dockerised, with an LLM pipeline that has deterministic guardrails against fabrication.

---

## Why this exists

Tailoring a CV to each posting is slow and repetitive, and most "AI résumé" tools happily invent experience to match the job — which is worse than useless when a real interview follows. This project does the tailoring automatically while treating one rule as non-negotiable: **the output may only rephrase and reorder what's actually in your CV, never add to it.** That constraint is enforced in code, not left to a prompt's good intentions.

---

## Features

- **One-step generation** — paste a job URL, get a tailored CV and cover letter as ATS-safe PDFs.
- **Grounded in your real CV** — a deterministic fact-preservation guard diffs the documents before and after the "humanize" pass and rejects any rewrite that invents or drops a fact.
- **ATS-safe by construction** — single-column layout, real selectable text (not an image), standard section headings in the posting's language, a header photo floated so it never breaks the linear reading order parsers depend on.
- **Reads naturally** — a humanize pass strips typical "AI-written" markers (filler, triads, signposting, hedging) so the documents don't read as machine-generated.
- **Application tracker** — every run appends a row to an Excel file with a status dropdown; managed from the web UI.
- **Web UI** — a calm, monochrome two-page app: a Generate page and an Applications table with per-row download / status / hide actions, an Active/Hidden filter, and an optional manual-text input for sites that block automated fetching.
- **No bot-protection bypass** — if a site blocks automated requests, you paste the posting text instead; nothing is circumvented.

---

## Tech stack

**Backend** — Python 3.11 · FastAPI · Uvicorn · Anthropic Claude (configurable model) · Requests + BeautifulSoup · WeasyPrint + Markdown (PDF) · openpyxl (Excel)

**Frontend** — Vite · React · TypeScript · React Router · self-hosted Inter

**Runtime** — Docker / Docker Compose. Python, the PDF system libraries (Pango), and ATS-friendly fonts all live in the image, so the only thing you install locally is Docker.

**Testing** — an extensive pytest suite (running into the high tens) executed inside the backend image against real WeasyPrint, covering the tracker schema invariants, the fact-preservation guard, the PDF rendering, and every API endpoint.

---

## Architecture

```
Job URL
  │
  ▼
fetch ──────────►  download + extract posting text   (manual-text fallback if blocked)
  │
  ▼
analyze ────────►  LLM → structured JobAnalysis (company, title, skills, location, …)
  │
  ▼
load profile ───►  your master CV + cover-letter template + personal data
  │
  ▼
tailor ─────────►  CV + cover letter, grounded in the profile, in the posting's language
  │
  ▼
humanize ───────►  de-AI rewrite  ─── fact-preservation guard ──► falls back to tailored text
  │                                    (rejects invented/dropped facts)
  ▼
render ─────────►  ATS-safe PDFs (WeasyPrint): selectable text, single column, header photo
  │
  ▼
place + track ──►  output/<Company>/  +  applications_tracker.xlsx
```

The same pipeline (`run_pipeline`) is exposed two ways: a CLI and a REST API. The frontend talks to the REST API; nothing about the core logic is duplicated.

---

## Design principles

Enforced in code and prompts, not left to chance:

- **No fabrication.** The CV and letter are built only from your master profile. A deterministic guard extracts factual tokens (numbers, years, tech names, contacts) and discards any rewrite that adds or removes one — so the tool cannot ship a skill you don't actually have. This was verified on a real run where the posting demanded a framework absent from the master CV, and the tailored CV correctly did **not** add it.
- **ATS-safe by construction.** The reading order, headings, and single-column structure are guaranteed by the layout, and a regression test pins the cover letter's structure so it can't silently drift.
- **Reversibility before risk.** Applications are _hidden_, never deleted; the generated files are never destroyed by the app. The Excel tracker migrates its schema lazily on write and never mutates on read.
- **Honest UI.** The 30–60s generation shows the real pipeline steps and an elapsed counter — no fake progress bar.

---

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Desktop or Engine + Compose v2)
- An [Anthropic API key](https://console.anthropic.com/)

No local Python or Node install is required — everything runs in Docker.

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/job-application-tailor.git
cd job-application-tailor

echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### 2. Create your profile

The `profile/` folder holds your personal data and is **gitignored** — you create it locally; it never enters the repository.

```
profile/
├── master_cv.md              # your full CV: all experience, skills, education
├── cover_letter_template.md  # a base cover letter (your tone, key points, sign-off)
├── personal.json             # contact details + languages
└── photo.jpg                 # optional CV header photo
```

`profile/personal.json`:

```json
{
  "full_name": "Your Name",
  "email": "you@example.com",
  "phone": "+49 ...",
  "location": "City, Country",
  "linkedin": "https://www.linkedin.com/in/...",
  "github": "https://github.com/...",
  "photo": "profile/photo.jpg",
  "languages": ["German (native)", "English (C1)"]
}
```

Only `full_name` and `email` are required. The richer your `master_cv.md`, the better the tailoring — the tool selects and rephrases from it, never beyond it.

### 3. Run

```bash
docker compose up --build
```

- **Web UI** → `http://localhost:5173`
- **API + Swagger docs** → `http://localhost:8010/docs`

> The compose file maps the API to host port **8010** to avoid clashing with other local services. Adjust it in `docker-compose.yml` if needed; the frontend reads the API location from `VITE_API_URL`.

---

## Using the web UI

**Generate** — paste a job URL and click generate. Watch the real pipeline steps run (~30–60s), then download the tailored CV and cover letter. If the site blocks automated fetching (Indeed, LinkedIn, some SPAs), expand the manual-text field and paste the description — the URL is still recorded.

**Applications** — a table of every application: company, size, posting link, employment type, role, **city**, status, and date. Per row you can download the CV and cover letter, toggle the status (synced to the Excel dropdown), and hide it. A filter switches between **Active** and **Hidden**.

---

## Using the API

| Method  | Endpoint                        | Description                                                                                                                    |
| ------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------- |
| `POST`  | `/generate`                     | Body `{ "url": "...", "text"?: "...", "lang"?: "..." }`. Runs the full pipeline; returns the analysis, company, and file URLs. |
| `GET`   | `/applications`                 | List applications. `?include_hidden=true` includes hidden ones.                                                                |
| `PATCH` | `/applications/{id}/status`     | Body `{ "status": "..." }`.                                                                                                    |
| `PATCH` | `/applications/{id}/visibility` | Body `{ "hidden": true                                                                                                         | false }`. |
| `GET`   | `/files/{company}/{filename}`   | Download a generated PDF.                                                                                                      |

```bash
curl -X POST http://localhost:8010/generate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/jobs/frontend-developer"}'
```

`text` is optional and only needed when a site blocks automated fetching.

### CLI

```bash
docker compose run --rm backend python -m backend.apply "https://example.com/jobs/12345"
```

Options: `--text-file PATH`, `--lang LANG`, `--output-dir PATH`, `--no-photo`.

---

## Output

```
output/
├── applications_tracker.xlsx
└── <Company>/
    ├── CV_<Name>_<Company>.pdf
    ├── CoverLetter_<Name>_<Company>.pdf
    └── _drafts/                  # intermediate markdown, editable
        ├── cv.md
        └── cover_letter.md
```

Re-running for the same company creates a numerically suffixed folder rather than overwriting.

---

## Configuration

| Variable            | Default                 | Purpose                                             |
| ------------------- | ----------------------- | --------------------------------------------------- |
| `ANTHROPIC_API_KEY` | —                       | Required.                                           |
| `ANTHROPIC_MODEL`   | Claude Sonnet           | Model used for analysis, tailoring, and humanizing. |
| `FRONTEND_ORIGIN`   | `http://localhost:5173` | Allowed CORS origin(s), comma-separated.            |
| `VITE_API_URL`      | `http://localhost:8010` | API base URL the frontend calls.                    |

---

## Privacy

`profile/` (your CV, photo, contacts), `output/` (generated documents and the tracker), and `.env` (your API key) are all gitignored and stay on your machine. Check `git status` before committing so none of your personal data is pushed.

---

## Deployment notes

The frontend is a static Vite build and deploys cleanly to any static host (e.g. Vercel), pointed at the backend via `VITE_API_URL`. The **backend cannot run on serverless platforms** — it needs WeasyPrint's system libraries, long-running requests, and a persistent file for the tracker — so it belongs on a container host (Railway, Render, Fly.io, or any Docker-capable VPS). The current build is a single-user local tool; a shared multi-user deployment would additionally need per-user profiles, per-user storage, and authentication.

---

## Acknowledgments

- The humanize pass builds on the patterns in [blader/humanizer](https://github.com/blader/humanizer) (MIT).
- The monochrome visual direction follows a Cal.com-style design system.

---

## Disclaimer

This tool tailors and rephrases your real CV to fit a posting; it is designed **not** to fabricate experience. You are responsible for the accuracy of your `profile/` data and for reviewing every generated document before sending it.

---

## License

Add a license of your choice (e.g. [MIT](https://choosealicense.com/licenses/mit/)) in a `LICENSE` file.
