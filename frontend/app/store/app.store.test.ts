import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from './app.store';

describe('useAppStore — Estado general de la aplicación', () => {
	beforeEach(() => {
		useAppStore.getState().resetProjectState();
	});

	it('debe inicializar hasUnsavedChanges como false', () => {
		expect(useAppStore.getState().hasUnsavedChanges).toBe(false);
	});

	it('debe inicializar pendingNavigationPath como null', () => {
		expect(useAppStore.getState().pendingNavigationPath).toBeNull();
	});

	it('debe limpiar el estado al llamar resetProjectState', () => {
		useAppStore.getState().setHasUnsavedChanges(true);
		useAppStore.getState().setPendingNavigationPath('/alguna-ruta');

		useAppStore.getState().resetProjectState();

		const state = useAppStore.getState();
		expect(state.hasUnsavedChanges).toBe(false);
		expect(state.pendingNavigationPath).toBeNull();
	});
});
