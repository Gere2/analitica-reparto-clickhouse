FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios (seguridad de Docker)
RUN adduser --disabled-password --gecos '' appuser
COPY --chown=appuser . .
USER appuser

EXPOSE 8080
CMD ["python", "app.py"]
