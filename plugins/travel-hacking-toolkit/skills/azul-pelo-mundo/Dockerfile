FROM ghcr.io/borski/patchright-docker:latest

COPY scripts/search_azul.py /app/search_azul.py
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV AZUL_IN_DOCKER=1

ENTRYPOINT ["/app/entrypoint.sh"]
