FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /tmp/kosmo-runner \
 && chown -R node:node /tmp/kosmo-runner

COPY server.js /app/server.js
USER node:node
WORKDIR /app
EXPOSE 8081
ENTRYPOINT ["node", "/app/server.js"]
