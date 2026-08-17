'use client';

import { useEffect, useRef } from 'react';
import { useAppStore } from 'app/store/app.store';

interface UseUnsavedChangesOptions {
	isDirty: boolean;
	onAutosave?: () => Promise<unknown> | void;
	autosaveDelayMs?: number;
	enabled?: boolean;
}

export function useUnsavedChanges({
	isDirty,
	onAutosave,
	autosaveDelayMs = 3000,
	enabled = true,
}: UseUnsavedChangesOptions) {
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);

	// Propaga el estado "dirty" al store global
	useEffect(() => {
		setHasUnsavedChanges(enabled && isDirty);
		return () => {
			setHasUnsavedChanges(false);
		};
	}, [enabled, isDirty, setHasUnsavedChanges]);

	// Al guardar (o quedar limpio), la navegación pendiente deja de tener sentido
	useEffect(() => {
		if (isDirty) return;
		const timer = window.setTimeout(() => setPendingNavigationPath(null), 0);
		return () => window.clearTimeout(timer);
	}, [isDirty, setPendingNavigationPath]);

	const onAutosaveRef = useRef(onAutosave);
	useEffect(() => {
		onAutosaveRef.current = onAutosave;
	}, [onAutosave]);

	// Autosave con debounce
	useEffect(() => {
		if (!enabled || !isDirty || !onAutosave) return;
		const timer = window.setTimeout(() => {
			void onAutosaveRef.current?.();
		}, autosaveDelayMs);
		return () => window.clearTimeout(timer);
	}, [enabled, isDirty, autosaveDelayMs, onAutosave]);

	// Guards de salida (recarga y navegación del historial)
	useEffect(() => {
		if (!enabled) return;

		const handleBeforeUnload = (e: BeforeUnloadEvent) => {
			if (useAppStore.getState().hasUnsavedChanges) {
				e.preventDefault();
			}
		};

		const handlePopState = () => {
			if (useAppStore.getState().hasUnsavedChanges) {
				setPendingNavigationPath(window.location.href);
			}
		};

		window.addEventListener('beforeunload', handleBeforeUnload);
		window.addEventListener('popstate', handlePopState);

		return () => {
			window.removeEventListener('beforeunload', handleBeforeUnload);
			window.removeEventListener('popstate', handlePopState);
		};
	}, [enabled, setPendingNavigationPath]);
}
