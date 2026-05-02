FROM ghcr.io/borski/patchright-docker:latest

WORKDIR /app
COPY scripts/check_balance.py .

# Persistent profile directory inside container
RUN mkdir -p /root/.aa-browser-profiles

ENTRYPOINT ["sh", "-c", "Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &\nexport DISPLAY=:99\nsleep 1\npython3 /app/check_balance.py \"$@\"", "--"]
