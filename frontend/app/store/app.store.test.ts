import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from './app.store';

describe('useAppStore — Estado general de la aplicación', () => {
	beforeEach(() => {
		useAppStore.getState().resetProjectState();
	});

	it('debe inicializar currentProject como null', () => {
		expect(useAppStore.getState().currentProject).toBeNull();
	});

	it('debe inicializar hasUnsavedChanges como false', () => {
		expect(useAppStore.getState().hasUnsavedChanges).toBe(false);
	});

	it('debe inicializar pendingNavigationPath como null', () => {
		expect(useAppStore.getState().pendingNavigationPath).toBeNull();
	});

	it('debe limpiar el estado del proyecto al llamar resetProjectState', () => {
		useAppStore.getState().setCurrentProject({ id: 'proj_01', name: 'Test' } as never);
		useAppStore.getState().setHasUnsavedChanges(true);
		useAppStore.getState().setPendingNavigationPath('/alguna-ruta');

		useAppStore.getState().resetProjectState();

		const state = useAppStore.getState();
		expect(state.currentProject).toBeNull();
		expect(state.hasUnsavedChanges).toBe(false);
		expect(state.pendingNavigationPath).toBeNull();
	});
});
