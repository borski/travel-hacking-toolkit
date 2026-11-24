FROM ghcr.io/borski/patchright-docker:latest

COPY scripts/search_viajanet.py /app/search_viajanet.py
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV VIAJANET_IN_DOCKER=1

ENTRYPOINT ["/app/entrypoint.sh"]
