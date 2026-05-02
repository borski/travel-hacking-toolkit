FROM ghcr.io/borski/patchright-docker:latest

WORKDIR /app
COPY scripts/search_fares.py .
COPY scripts/check_change.py .
COPY scripts/monitor.py .
COPY scripts/entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
