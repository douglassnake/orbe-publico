FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --create-home api
COPY app.py ./app.py
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY static ./static
USER api
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app:app --host 0.0.0.0 --port 8000"]
