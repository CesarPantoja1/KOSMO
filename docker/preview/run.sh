#!/bin/sh
# KOSMO preview: un servidor por proyecto activo.
#
# Escanea los markers de /workspaces/.preview-active (escritos por el backend tras
# cada implementación exitosa) y levanta un `next dev` por proyecto en un puerto
# propio. Publica el mapeo en /workspaces/.preview-ports.json:
#
#   { "<project_id>": { "port": 3000, "host_port": 3001, "workspace": "/workspaces/<project_id>", "url": "http://localhost:3001" } }
#
# Puertos: container port = CONTAINER_BASE + i, host port = HOST_BASE + i
# (compose mapea el rango 3001-3016 -> 3000-3015 por defecto).
set -eu

MARKERS_DIR="${MARKERS_DIR:-/workspaces/.preview-active}"
PORTS_FILE="${PORTS_FILE:-/workspaces/.preview-ports.json}"
CONTAINER_BASE="${CONTAINER_BASE:-3000}"
HOST_BASE="${HOST_BASE:-3001}"
SLEEP="${SLEEP:-5}"
MAX_PREVIEWS="${MAX_PREVIEWS:-16}"
STATE_DIR="/tmp/preview-state"

mkdir -p "$MARKERS_DIR" "$STATE_DIR"

container_port_for() { echo $((CONTAINER_BASE + $1)); }
host_port_for() { echo $((HOST_BASE + $1)); }

stop_project() {
    pidfile="$STATE_DIR/$1"
    [ -f "$pidfile" ] || return 0
    pid=$(awk '{print $1}' "$pidfile")
    kill "$pid" 2>/dev/null || true
    rm -f "$pidfile"
    echo "[preview] detenido $1"
}

start_project() {
    project_id="$1"
    workspace="$2"
    port="$3"
    if [ ! -d "$workspace/node_modules" ]; then
        echo "[preview] instalando dependencias de $project_id"
        (cd "$workspace" && npm install) >/tmp/"$project_id"-npm-install.log 2>&1 || {
            echo "[preview] no se pudieron instalar dependencias de $project_id"
            return 1
        }
    fi
    (cd "$workspace" && exec npm run dev -- -H 0.0.0.0 -p "$port") >/tmp/"$project_id"-next.log 2>&1 &
    pid=$!
    echo "$pid $port" > "$STATE_DIR/$project_id"
    echo "[preview] sirviendo $project_id ($workspace) en :$port"
}

write_manifest() {
    manifest=""
    first=1
    for entry in "$@"; do
        project_id=$(echo "$entry" | cut -d'|' -f1)
        container_port=$(echo "$entry" | cut -d'|' -f2)
        host_port=$(echo "$entry" | cut -d'|' -f3)
        workspace=$(echo "$entry" | cut -d'|' -f4)
        url="http://localhost:$host_port"
        if [ "$first" -eq 1 ]; then
            manifest="  \"$project_id\": {\"port\": $container_port, \"host_port\": $host_port, \"workspace\": \"$workspace\", \"url\": \"$url\"}"
            first=0
        else
            manifest="$manifest,
  \"$project_id\": {\"port\": $container_port, \"host_port\": $host_port, \"workspace\": \"$workspace\", \"url\": \"$url\"}"
        fi
    done
    printf '{\n%s\n}\n' "$manifest" > "${PORTS_FILE}.tmp"
    mv "${PORTS_FILE}.tmp" "$PORTS_FILE"
}

reconcile() {
    i=0
    entries=""
    for marker in $(ls "$MARKERS_DIR" 2>/dev/null | sort); do
        [ -f "$MARKERS_DIR/$marker" ] || continue
        if [ "$i" -ge "$MAX_PREVIEWS" ]; then
            echo "[preview] límite de $MAX_PREVIEWS previews activas alcanzado"
            break
        fi
        project_id="$marker"
        workspace=$(cat "$MARKERS_DIR/$marker" | tr -d '[:space:]')
        container_port=$(container_port_for "$i")
        host_port=$(host_port_for "$i")

        running=1
        if [ -f "$STATE_DIR/$project_id" ]; then
            pid=$(awk '{print $1}' "$STATE_DIR/$project_id")
            old_port=$(awk '{print $2}' "$STATE_DIR/$project_id")
            if ! kill -0 "$pid" 2>/dev/null; then
                start_project "$project_id" "$workspace" "$container_port" || running=0
            elif [ "$old_port" != "$container_port" ]; then
                echo "[preview] puerto cambiado para $project_id ($old_port -> $container_port)"
                stop_project "$project_id"
                start_project "$project_id" "$workspace" "$container_port" || running=0
            fi
        else
            start_project "$project_id" "$workspace" "$container_port" || running=0
        fi

        if [ "$running" -eq 1 ]; then
            entries="$entries
$project_id|$container_port|$host_port|$workspace"
            i=$((i + 1))
        fi
    done

    # Detener proyectos cuyo marker desapareció (workspace eliminado)
    for pidfile in "$STATE_DIR"/*; do
        [ -f "$pidfile" ] || continue
        project_id=$(basename "$pidfile")
        if [ ! -f "$MARKERS_DIR/$project_id" ]; then
            stop_project "$project_id"
        fi
    done

    write_manifest $entries
}

echo "[preview] escaneando $MARKERS_DIR (puertos host $HOST_BASE+, container $CONTAINER_BASE+)..."
while true; do
    reconcile
    sleep "$SLEEP"
done
