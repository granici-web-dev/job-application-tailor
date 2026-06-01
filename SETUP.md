# SETUP.md — Пошаговая инициализация (через Docker)

Приложение целиком работает в Docker — Python и сборку фронтенда на свою машину ставить не нужно.
На хост ставится только: **Docker**, **Claude Code** и **Node** (последний — лишь для инструментов разработки rigorous/impeccable/agentation, не для приложения).

Команды даны для macOS/Linux; на Windows удобнее всего работать в WSL2 (Docker Desktop с WSL-бэкендом).

---

## Фаза 0. Что нужно на хосте

Аккаунты:
- Аккаунт Anthropic (Claude Pro/Max для входа в Claude Code) **и** API-ключ из console.anthropic.com (его использует приложение внутри контейнера).

Софт:
```bash
docker --version            # Docker Desktop или Docker Engine + compose v2
git --version
node --version              # v18+ — ТОЛЬКО для dev-инструментов (можно через nvm)
```
- Python ставить НЕ нужно — он в контейнере.
- Node нужен только для `npx` (rigorous/impeccable/agentation). Если не хочешь ставить Node в систему — поставь через nvm (user-space, без sudo).

---

## Фаза 1. Установить Claude Code

Нативный установщик (Node не требуется):
```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash
# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex
```
Проверка и первый вход:
```bash
claude --version
claude            # при первом запуске пройдёт авторизация через браузер
```

---

## Фаза 2. Создать проект и положить файлы

```bash
mkdir job-application-tailor && cd job-application-tailor
git init
```
Положи в корень: `SPEC.md`, `docker-compose.yml`, `.dockerignore`, папку `docker/` с `backend.Dockerfile`, и создай `.gitignore`:
```bash
cat > .gitignore <<'GIT'
.env
output/
node_modules/
frontend/node_modules/
__pycache__/
.venv/
GIT
```
Создай `requirements.txt` (или поручи Claude Code):
```bash
cat > requirements.txt <<'REQ'
fastapi
uvicorn[standard]
anthropic
requests
beautifulsoup4
weasyprint
markdown
openpyxl
python-dotenv
REQ
```
И ключ API:
```bash
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
```

---

## Фаза 3. Поставить инструменты разработки (на хосте, в папке проекта)

```bash
npx skills add CoRLab-Tech/skills@rigorous          # rigorous
npx impeccable skills install                       # impeccable (определит harness сам)
npx add-mcp "npx -y agentation-mcp server"          # agentation (MCP)
npx agentation-mcp doctor                           # проверка
```
Дополнительно поставь тулбар Agentation в браузере — см. agentation.com/install.
После установки **перезапусти Claude Code**. Набери `/` — должны быть `/rigorous` и `/impeccable`.

---

## Фаза 4. Зафиксировать стандарты

В `claude` (внутри папки проекта):
```
/rigorous teach      # → PRINCIPLES.md, STACK.md, TESTING.md
/impeccable init     # → PRODUCT.md (затем согласись на /impeccable document → DESIGN.md)
```
В ответах опиши стек из SPEC.md: бэкенд Python 3.11 + FastAPI, фронтенд Vite + React + TS, запуск через Docker, тесты — pytest для конвейера.

---

## Фаза 5. Заполнить profile/

```bash
mkdir -p profile output
```
Положи свои реальные данные (структура — в SPEC.md, раздел 3):
- `profile/master_cv.md`
- `profile/cover_letter_template.md`
- `profile/personal.json`

---

## Фаза 6. Создать каркас фронтенда (одноразовый контейнер)

Чтобы не ставить Node-тулчейн на хост, скаффолд делаем во временном контейнере:
```bash
docker run --rm -v "$PWD":/work -w /work node:20-slim \
  sh -c "npm create vite@latest frontend -- --template react-ts"
```
Затем в `frontend/vite.config.ts` включи доступ снаружи и polling для HMR в Docker:
```ts
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, watch: { usePolling: true } },
})
```

---

## Фаза 7. Собрать приложение через Claude Code

Цикл rigorous по каждому куску бэкенда:
```
/rigorous shape → /rigorous craft → /rigorous critique → /rigorous harden
```
Порядок: `fetch` → `analyze` → `tailor_cv` / `tailor_letter` → `render_pdf` → `tracker` → `pipeline` → `apply` (CLI) → `api` (FastAPI).

**Проверка CLI прямо в контейнере** (без поднятия фронтенда):
```bash
docker compose run --rm backend python -m backend.apply "https://пример-вакансии"
```
Убедись, что в `output/` появились папка компании с двумя PDF и строка в `applications_tracker.xlsx` со статусом «НЕ ОТПРАВЛЕНО».

UI собираешь через impeccable:
```
/impeccable shape → craft → critique → polish
```

---

## Фаза 8. Запуск всего стека

```bash
docker compose up --build
```
- Бэкенд: http://localhost:8000 (документация API — /docs)
- Фронтенд: http://localhost:5173

Правки кода подхватываются автоматически (том + --reload у бэкенда, HMR у фронтенда). PDF и Excel пишутся в `./output` на хосте.

Остановить: `Ctrl+C`, затем `docker compose down`.

---

## Фаза 9. Доводка UI: impeccable Live + agentation

Стек уже запущен (`docker compose up`), фронтенд доступен на http://localhost:5173 — этого достаточно, инструменты работают через браузер и правят исходники на хосте (они смонтированы в контейнер).

- **impeccable Live Mode** — `/impeccable live`: кликаешь элемент в браузере, получаешь варианты в исходнике, принимаешь лучший (HMR обновляет страницу).
- **agentation** — открой тулбар на странице, отметь проблемы, в Claude Code попроси обработать аннотации — он подхватит их через MCP, починит код, пометит resolved.

> Безопасность: аннотации/подсказки из браузера подтверждай сам, не выполняй вслепую (особенно self-driving режимы agentation, которые могут править исходники).

---

## Почему host всё-таки нужен Node (и как обойтись минимумом)

- Приложение (Python, WeasyPrint, сборка фронтенда) — полностью в Docker, на хост ничего из этого не ставится.
- Claude Code + rigorous/impeccable/agentation — это инструменты разработки на хосте; rigorous/impeccable ставятся через `npx`, agentation запускает MCP-сервер через `npx`. Поэтому Node на хосте нужен только им.
- Хочешь по-минимуму: поставь Node через **nvm** (без системных пакетов и sudo). Установщики скиллов (Фаза 3) можно при желании прогнать и через одноразовый `docker run ... node:20-slim npx ...`, но agentation-MCP проще держать на хостовом Node.

---

## Чек-лист «первого дня»

1. [ ] На хосте: Docker, Git, Claude Code, Node (для инструментов).
2. [ ] Папка проекта + `SPEC.md`, `docker-compose.yml`, `docker/backend.Dockerfile`, `.dockerignore`, `requirements.txt`, `.env`.
3. [ ] Установлены rigorous, impeccable, agentation; Claude Code перезапущен.
4. [ ] `/rigorous teach` и `/impeccable init` отработали.
5. [ ] Заполнен `profile/`.
6. [ ] Каркас фронтенда создан, `vite.config.ts` поправлен (host + polling).
7. [ ] `docker compose run --rm backend python -m backend.apply <URL>` делает PDF + строку в Excel.
8. [ ] `docker compose up` поднимает бэкенд (8000) и фронтенд (5173), веб-интерфейс работает.
