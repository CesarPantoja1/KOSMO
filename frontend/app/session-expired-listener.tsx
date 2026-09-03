'use client';

import { useEffect } from 'react';
import { onSessionExpired } from '@/shared/lib/session-events';
import { clearAllStores } from '@/features/app-state';

/**
 * Composition root: conecta el evento genérico de sesión expirada (emitido
 * desde `shared/api`, que no puede depender de `features`) con la limpieza
 * real de stores de la aplicación (`features/app-state`).
 *
 * Este componente vive en `frontend/app` (fuera de `src`) porque es aquí
 * donde se permite conocer y componer todas las capas de FSD.
 */
export function SessionExpiredListener() {
	useEffect(() => {
		return onSessionExpired(() => {
			clearAllStores();
		});
	}, []);

	return null;
}
