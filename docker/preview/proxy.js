"use strict";

const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const manifestPath = process.env.PREVIEW_PORTS_FILE || "/workspaces/.preview-ports.json";
const previewHostSuffix = (process.env.PREVIEW_HOST_SUFFIX || "preview-kosmo.cespan.dev").toLowerCase();
const previewServiceHost = process.env.PREVIEW_SERVICE_HOST || "preview";
const previewPortStart = Number(process.env.PREVIEW_PORT_START || 3000);
const previewPortEnd = Number(process.env.PREVIEW_PORT_END || 3015);

function projectIdFromHost(hostHeader) {
  const host = String(hostHeader || "").split(":", 1)[0].toLowerCase();
  const suffix = `-${previewHostSuffix}`;
  if (!host.endsWith(suffix)) return null;
  const label = host.slice(0, -suffix.length);
  if (!/^prj-[0-9a-z]+$/.test(label)) return null;
  return `prj_${label.slice(4)}`;
}

function portForProject(projectId) {
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    const entry = Object.entries(manifest).find(([id]) => id.toLowerCase() === projectId);
    const port = Number(entry && entry[1] && entry[1].port);
    return Number.isInteger(port) && port >= previewPortStart && port <= previewPortEnd ? port : null;
  } catch {
    return null;
  }
}

function resolveTarget(req) {
  const projectId = projectIdFromHost(req.headers.host);
  return projectId ? portForProject(projectId) : null;
}

function reject(res, statusCode) {
  res.writeHead(statusCode, { "content-type": "text/plain; charset=utf-8" });
  res.end(statusCode === 404 ? "Vista previa no disponible" : "Host de vista previa inválido");
}

const server = http.createServer((req, res) => {
  const port = resolveTarget(req);
  if (port === null) return reject(res, 404);
  const upstream = http.request({
    hostname: previewServiceHost,
    port,
    method: req.method,
    path: req.url,
    headers: { ...req.headers, host: `${previewServiceHost}:${port}` },
  }, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
    upstreamRes.pipe(res);
  });
  upstream.on("error", () => reject(res, 502));
  req.pipe(upstream);
});

server.on("upgrade", (req, socket, head) => {
  const port = resolveTarget(req);
  if (port === null) return socket.destroy();
  const upstream = net.connect(port, previewServiceHost, () => {
    const headers = Object.entries({ ...req.headers, host: `${previewServiceHost}:${port}` })
      .map(([name, value]) => `${name}: ${value}`)
      .join("\r\n");
    upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n${headers}\r\n\r\n`);
    if (head.length) upstream.write(head);
    socket.pipe(upstream).pipe(socket);
  });
  upstream.on("error", () => socket.destroy());
});

server.listen(8082, "0.0.0.0");
