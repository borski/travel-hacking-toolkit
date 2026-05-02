FROM ghcr.io/borski/patchright-docker:latest

COPY scripts/search_flights.py /app/search_flights.py

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["script", "/app/search_flights.py"]
