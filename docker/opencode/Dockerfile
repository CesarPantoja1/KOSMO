# syntax=docker/dockerfile:1.7
# OpenCode is installed while building the image, never during container start.
# Updating it is an explicit reviewed change through OPENCODE_VERSION.
FROM node:22-bookworm-slim

ARG OPENCODE_VERSION=1.18.19

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install --global --omit=dev "opencode-ai@${OPENCODE_VERSION}" \
 && mkdir -p /home/node/.config/opencode \
 && chown -R node:node /home/node

COPY start.sh /usr/local/bin/start-opencode
RUN chmod 0555 /usr/local/bin/start-opencode

USER node:node
WORKDIR /workspaces

EXPOSE 4096

ENTRYPOINT ["/usr/local/bin/start-opencode"]
