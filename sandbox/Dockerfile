FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 nftables ca-certificates && \
    rm -rf /var/lib/apt/lists/*
RUN useradd --uid 1500 --create-home sandbox && mkdir -p /sandbox /app /opt/immune-canary && \
    chown sandbox:sandbox /sandbox && printf 'public-negative-test-canary\n' > /opt/immune-canary/blocked.txt && \
    chmod 755 /opt/immune-canary && chmod 644 /opt/immune-canary/blocked.txt
COPY backend/target/*.py /app/backend/target/
COPY sandbox/worker.py /app/sandbox/worker.py
COPY sandbox/probe.py /app/sandbox/probe.py
WORKDIR /sandbox
USER sandbox
CMD ["sleep", "infinity"]
