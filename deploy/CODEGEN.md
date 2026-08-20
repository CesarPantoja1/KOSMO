# Operación de generación y custodia de código

Cada proyecto generado tiene un directorio identificado por su `project_id`.
PostgreSQL conserva metadata, propiedad y trazabilidad; el código, su template y su
historial Git se conservan en filesystem.

| Ambiente | Persistencia | Contenedores con acceso |
| --- | --- | --- |
| Desarrollo | volumen `kosmo_workspaces` | `backend`, `opencode`, `preview` |
| Staging | `/opt/kosmo/staging/workspaces` | `kosmo-staging-backend`, `kosmo-staging-opencode` |
| Producción | `/opt/kosmo/production/workspaces` | `kosmo-backend`, `kosmo-opencode` |

El CD crea estos directorios y asigna UID/GID `1000`. No tienen puertos ni rutas HTTP
públicas. El usuario accede a sus archivos mediante las rutas autenticadas de KOSMO; un
administrador los inspecciona únicamente por SSH. Al borrar un proyecto, el backend borra
también su workspace y los metadatos de preview.

## Secretos de GitHub Environments

Crear el secreto protegido `STAGING_CODEGEN_ENV_FILE` en el Environment `staging` y
`PRODUCTION_CODEGEN_ENV_FILE` en el Environment `Production`. El workflow los agrega al
archivo existente de cada ambiente, de modo que no es necesario revelar ni reemplazar el
secreto histórico `*_ENV_FILE`.

```dotenv
OPENCODE_SERVER_PASSWORD=<secreto-aleatorio-largo>
OPENCODE_MODEL=deepseek/deepseek-v4-flash
DEEPSEEK_API_KEY=<clave-de-proveedor-limitada-a-generacion>
CODE_RUNNER_TOKEN=<secreto-aleatorio-distinto>
```

Para otros modelos usar `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` o `GEMINI_API_KEY`.
`LLM_API_KEY` sigue siendo la clave de la API de KOSMO; separar una credencial limitada
para OpenCode es preferible. El CD publica `kosmo-opencode:sha-<commit>` y nunca instala
`latest` al iniciar el contenedor.

## Inspección y backup

```bash
# En la VM de producción, lectura exclusivamente
sudo find /opt/kosmo/production/workspaces -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
sudo du -sh /opt/kosmo/production/workspaces/*
sudo -u '#1000' git -C /opt/kosmo/production/workspaces/<project_id> log --oneline -n 20

# Backup diario: conservar también el backup consistente de PostgreSQL
sudo install -d -m 0700 /var/backups/kosmo
sudo tar -C /opt/kosmo/production -czf /var/backups/kosmo/workspaces-$(date +%F).tgz workspaces
```

Respaldar PostgreSQL y `workspaces` juntos en almacenamiento cifrado externo, con al menos
30 días de retención. Para restaurar: detener `backend` y `opencode`, restaurar primero
PostgreSQL, extraer el archive en `/opt/kosmo/production`, volver a asignar UID 1000 y
validar la lectura autenticada de un archivo antes de reanudar generación.

## Límites de despliegue

OpenCode y `code-runner` tienen 1.5 CPU, 2 GiB, 256 PIDs y sin capacidades Linux añadidas.
El runner recibe un archive temporal del workspace, no el volumen persistente ni secretos de
la aplicación; se destruye tras validar. La API conserva un solo worker porque el broker de
eventos actual vive en memoria. La preview con `next dev`
es local: no habilitar 4096 ni 3001-3016 en firewall, Cloudflare Tunnel o Nginx hasta contar
con un gateway de preview autenticado y sandbox dedicado.
