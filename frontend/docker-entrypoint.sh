#!/bin/sh
set -eu

# NEXT_PUBLIC_* se incrusta durante `next build`. Esta aplicación se promueve
# entre staging y producción como la misma imagen, por lo que los identificadores
# OAuth y el dominio público se publican en un archivo estático generado al
# arrancar el contenedor. No añadir secretos a esta lista.
node -e '
const config = {
  githubClientId: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "",
  githubScopes: process.env.NEXT_PUBLIC_GITHUB_SCOPES || "repo",
  railwayClientId: process.env.NEXT_PUBLIC_RAILWAY_CLIENT_ID || "",
  railwayScopes: process.env.NEXT_PUBLIC_RAILWAY_SCOPES || "openid email profile offline_access workspace:admin",
  publicAppDomain: process.env.NEXT_PUBLIC_DOMAIN_APP || "",
};
const json = JSON.stringify(config).replace(/</g, "\\u003c");
require("node:fs").writeFileSync(
  "/app/public/runtime-config.js",
  `window.__KOSMO_RUNTIME_CONFIG__ = ${json};\n`,
);
'

exec "$@"
