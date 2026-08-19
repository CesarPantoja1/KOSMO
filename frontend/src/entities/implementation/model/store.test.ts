import { beforeEach, describe, expect, it, vi } from 'vitest';
import { generateImplementation } from '../api/api';
import { clearImplementationStore, useImplementationStore } from './store';
import type { ImplementationSummary } from './types';

vi.mock('../api/api', () => ({
	generateImplementation: vi.fn(),
}));

const mockedGenerate = vi.mocked(generateImplementation);

const aSummary: ImplementationSummary = {
	featureId: 'feat_01',
	featureTitle: 'Registrar gastos',
	featureDisplayId: 'F-01',
	status: 'completed',
	metrics: [],
	technologies: [],
	nextSteps: [],
	generatedAt: '2026-08-19T10:00:00Z',
};

describe('useImplementationStore', () => {
	beforeEach(() => {
		clearImplementationStore();
		mockedGenerate.mockReset();
	});

	it('marca completed y registra la implementación al terminar', async () => {
		// Arrange
		mockedGenerate.mockResolvedValue(aSummary);

		// Act
		await useImplementationStore
			.getState()
			.startGeneration('feat_01', 'Registrar gastos', 'F-01');

		// Assert
		expect(useImplementationStore.getState().status).toBe('completed');
		expect(useImplementationStore.getState().summary).toEqual(aSummary);
		expect(useImplementationStore.getState().implementations['feat_01']).toBe(true);
	});

	it('actualiza el progreso con los mensajes emitidos por el flujo', async () => {
		// Arrange
		mockedGenerate.mockImplementation(
			async (_id, _title, _displayId, onProgress) => {
				onProgress?.('Generando código...');
				return aSummary;
			},
		);

		// Act
		await useImplementationStore
			.getState()
			.startGeneration('feat_01', 'Registrar gastos', 'F-01');

		// Assert
		expect(useImplementationStore.getState().progress).toBeNull();
	});

	it('marca failed y guarda el mensaje si la generación lanza error', async () => {
		// Arrange
		mockedGenerate.mockRejectedValue(new Error('fallo de validación'));

		// Act
		await useImplementationStore
			.getState()
			.startGeneration('feat_01', 'Registrar gastos', 'F-01');

		// Assert
		expect(useImplementationStore.getState().status).toBe('failed');
		expect(useImplementationStore.getState().errorMessage).toBe('fallo de validación');
		expect(useImplementationStore.getState().implementations['feat_01']).toBeUndefined();
	});
});
