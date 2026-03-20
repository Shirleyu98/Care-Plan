FROM python:3.12-slim

# Force Python to flush stdout/stderr immediately — essential in Docker
# Without this, output is buffered and lost when the container exits
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "--noreload", "0.0.0.0:8000"]