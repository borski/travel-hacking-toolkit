FROM ghcr.io/borski/patchright-docker:latest

WORKDIR /app
COPY scripts/taw_common.py .
COPY scripts/search_hotels.py .
COPY scripts/search_cars.py .
COPY scripts/browse_tickets.py .
COPY scripts/entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
