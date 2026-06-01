FROM python:3.11-slim

# Системные библиотеки для WeasyPrint (рендеринг PDF) + шрифты.
# fonts-liberation даёт метрически совместимые с Arial/Helvetica шрифты — удобно для ATS-резюме.
# Точный набор зависит от версии WeasyPrint; для современных версий (>=53) достаточно Pango.
# Если сборка PDF ругается на отсутствие библиотек — добавьте недостающие сюда.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libffi8 \
        fonts-liberation \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала зависимости — лучше кэшируется
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код копируется для standalone-сборки; в dev он же монтируется томом (см. docker-compose.yml)
COPY backend ./backend
COPY prompts ./prompts

EXPOSE 8000

# Dev-режим с автоперезагрузкой; в проде убрать --reload
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
