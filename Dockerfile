FROM python:3.12-slim

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV PORT=5000
EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:5000/health').status==200 else sys.exit(1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--chdir", "app", "app:app"]
