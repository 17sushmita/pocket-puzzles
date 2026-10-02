FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home puzzles
COPY app.py ./
COPY puzzle ./puzzle
COPY migrations ./migrations
COPY client ./client
COPY scripts/start.sh ./scripts/start.sh
USER puzzles
CMD ["sh", "scripts/start.sh"]
