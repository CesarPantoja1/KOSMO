type Listener = () => void;

const listeners = new Set<Listener>();

/**
 * Emite el evento de sesión expirada. `shared` no conoce quién escucha
 * (features/app-state, en la composición raíz de `frontend/app`), evitando
 * así que esta capa dependa de capas superiores.
 */
export function emitSessionExpired(): void {
	listeners.forEach((listener) => listener());
}

/**
 * Se suscribe al evento de sesión expirada. Devuelve una función para
 * cancelar la suscripción.
 */
export function onSessionExpired(listener: Listener): () => void {
	listeners.add(listener);
	return () => listeners.delete(listener);
}
