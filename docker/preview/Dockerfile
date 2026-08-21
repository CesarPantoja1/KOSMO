FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 make g++ ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY run.sh /app/run.sh
COPY proxy.js /app/proxy.js
RUN chmod 0555 /app/run.sh /app/proxy.js

USER node:node
WORKDIR /app
