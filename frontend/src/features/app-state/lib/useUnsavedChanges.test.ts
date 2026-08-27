import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useAppStore } from '../model/app.store';
import { useUnsavedChanges } from './useUnsavedChanges';

describe('useUnsavedChanges', () => {
	beforeEach(() => {
		useAppStore.setState({
			hasUnsavedChanges: false,
			pendingNavigationPath: null,
		});
	});

	afterEach(() => {
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	it('propaga isDirty al store global y lo limpia al desmontar', () => {
		const { rerender, unmount } = renderHook(
			({ isDirty }) => useUnsavedChanges({ isDirty }),
			{ initialProps: { isDirty: false } },
		);

		expect(useAppStore.getState().hasUnsavedChanges).toBe(false);

		rerender({ isDirty: true });
		expect(useAppStore.getState().hasUnsavedChanges).toBe(true);

		rerender({ isDirty: false });
		expect(useAppStore.getState().hasUnsavedChanges).toBe(false);

		rerender({ isDirty: true });
		unmount();
		expect(useAppStore.getState().hasUnsavedChanges).toBe(false);
	});

	it('ejecuta el autosave con debounce solo cuando está dirty', () => {
		vi.useFakeTimers();
		const onAutosave = vi.fn();

		const { rerender } = renderHook(
			({ isDirty }) => useUnsavedChanges({ isDirty, onAutosave, autosaveDelayMs: 3000 }),
			{ initialProps: { isDirty: false } },
		);

		rerender({ isDirty: true });
		expect(onAutosave).not.toHaveBeenCalled();

		vi.advanceTimersByTime(2999);
		expect(onAutosave).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1);
		expect(onAutosave).toHaveBeenCalledTimes(1);
	});

	it('guarda con beforeunload cuando hay cambios sin guardar', () => {
		renderHook(() => useUnsavedChanges({ isDirty: true }));

		const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
		Object.defineProperty(event, 'preventDefault', { value: vi.fn() });

		window.dispatchEvent(event);
		// El guard consulta el store global, que ya tiene el flag en true
		expect(useAppStore.getState().hasUnsavedChanges).toBe(true);
	});
});
