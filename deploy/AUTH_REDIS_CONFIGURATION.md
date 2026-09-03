# Autenticación y Redis para Staging y Producción

Los stacks canónicos son `deploy/staging/compose.yaml` y
`deploy/production/compose.yaml`. Ambos ejecutan Redis en la misma VM y red
Docker que el backend. Redis no publica el puerto `6379` al host ni a Internet.

El workflow une `STAGING_ENV_FILE` o `PRODUCTION_ENV_FILE` con la configuración
de codegen y lo entrega como `.env` de la VM. Agrega las siguientes variables al
secreto protegido correspondiente; sustituye cada marcador sin copiar secretos
entre ambientes:

```dotenv
# Persistencia y autenticación
DATABASE_URL=postgresql+asyncpg://<usuario>:<password>@<host>/<database>
REDIS_PASSWORD=<valor-base64url-distinto-por-ambiente>
REDIS_URL=redis://:<mismo-REDIS_PASSWORD>@redis:6379/0
FERNET_MASTER_KEY=<clave-fernet-distinta-por-ambiente>
JWT_ISSUER=kosmo
JWT_AUDIENCE=kosmo-api
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=604800
AUTH_DISABLED=false

# OAuth de GitHub y Railway. Los NEXT_PUBLIC_* se publican en el navegador;
# no pongas secretos en ellos. Deben existir en ambos ambientes.
GITHUB_CLIENT_ID=<id-oauth-de-github>
GITHUB_CLIENT_SECRET=<secreto-oauth-de-github>
NEXT_PUBLIC_GITHUB_CLIENT_ID=<mismo-id-publico-de-github>
NEXT_PUBLIC_GITHUB_SCOPES=repo
RAILWAY_CLIENT_ID=<id-oauth-de-railway>
RAILWAY_CLIENT_SECRET=<secreto-oauth-de-railway>
NEXT_PUBLIC_RAILWAY_CLIENT_ID=<mismo-id-publico-de-railway>
NEXT_PUBLIC_RAILWAY_SCOPES=openid email profile offline_access workspace:admin
NEXT_PUBLIC_DOMAIN_APP=https://<dominio-publico-del-ambiente>

# Runtime y navegador
ENV=staging
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://staging-kosmo.cespan.dev
OTEL_SERVICE_NAME=kosmo-backend
OTEL_ENVIRONMENT=staging
```

Para Production, usa `ENV=production`,
`CORS_ALLOWED_ORIGINS=https://kosmo.cespan.dev` y
`OTEL_ENVIRONMENT=production`. Usa una contraseña Redis con el
alfabeto Base64 URL-safe para que sea válida tanto como contraseña Redis como en
la URI. Por ejemplo, en una estación segura:

```bash
openssl rand -base64 48 | tr '+/' '-_' | tr -d '='
```

No uses `localhost` ni la IP pública de la VM en `REDIS_URL`: desde el
contenedor backend el nombre correcto es `redis`.

## OAuth: aplicaciones y callbacks

Registra en **cada** OAuth App (GitHub y Railway) exactamente estas URLs de
callback; no uses una URL comodín ni incluyas secretos en ellas:

```text
http://localhost:3000/perfil
https://staging-kosmo.cespan.dev/perfil
https://kosmo.cespan.dev/perfil
```

Para GitHub solicita únicamente `repo`. Para Railway usa una aplicación web
confidencial y los scopes configurados en `NEXT_PUBLIC_RAILWAY_SCOPES`.
`GITHUB_CLIENT_SECRET` y `RAILWAY_CLIENT_SECRET` permanecen solo en el secreto
protegido del ambiente; los valores `NEXT_PUBLIC_*` se escriben al inicio del
contenedor web en `runtime-config.js` y son deliberadamente públicos.

## Claves JWT de cada VM

Antes del primer despliegue, provisiona un par RSA distinto por ambiente en la
VM, fuera de Git y de los secretos de Actions. El contenedor se ejecuta como
UID/GID `1000`, por lo que ese usuario debe poder leer ambos archivos:

```bash
# Ejecutar en cada VM, tras transportar las claves por un canal seguro.
sudo install -d -o 1000 -g 1000 -m 0700 /opt/kosmo/<ambiente>/secrets
sudo install -o 1000 -g 1000 -m 0600 jwt_private.pem \
  /opt/kosmo/<ambiente>/secrets/jwt_private.pem
sudo install -o 1000 -g 1000 -m 0600 jwt_public.pem \
  /opt/kosmo/<ambiente>/secrets/jwt_public.pem
```

El workflow comprueba la existencia y lectura de estos archivos antes de correr
Alembic. No habilites `DEV_GENERATE_SECRETS` fuera de desarrollo.

## Operación

- `/health` es liveness del proceso; `/ready` confirma PostgreSQL y Redis.
- Redis usa AOF y un volumen Docker persistente. Respaldar el volumen junto con
  las claves y el backup consistente de PostgreSQL es responsabilidad de la VM.
- La imagen web no lleva una URL de API por ambiente: utiliza `/api` bajo el
  mismo dominio de Nginx. Esto permite promover el mismo digest de staging a
  producción sin redirigir el navegador hacia staging.
- `docker-compose.prod.yml` y `ENV_VARIABLES_GUIDE.md` son referencias
  históricas; los workflows usan exclusivamente los manifiestos de `deploy/`.
