import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/api', () => ({
	getDiagram: vi.fn(),
	generatePlantUmlDiagram: vi.fn(),
	deleteDiagram: vi.fn(),
}));

import { getDiagram, generatePlantUmlDiagram, deleteDiagram } from '../api/api';
import { useModelingStore, clearModelingStore } from './store';

const api = {
	getDiagram: vi.mocked(getDiagram),
	generatePlantUmlDiagram: vi.mocked(generatePlantUmlDiagram),
	deleteDiagram: vi.mocked(deleteDiagram),
};

describe('useModelingStore', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		clearModelingStore();
	});

	it('inicializa sin diagramas', () => {
		const state = useModelingStore.getState();
		expect(state.currentDiagrams).toEqual({});
		expect(state.hasDiagram).toEqual({});
	});

	it('getDiagram guarda el contenido y marca hasDiagram=true cuando hay contenido', async () => {
		// Arrange
		api.getDiagram.mockResolvedValue({
			id: 'd1',
			feature_id: 'f1',
			diagram_syntax: '@startuml',
			created_at: '',
			updated_at: '',
		});

		// Act
		const content = await useModelingStore.getState().getDiagram('prj_01', 'f1');

		// Assert
		expect(content).toBe('@startuml');
		expect(useModelingStore.getState().currentDiagrams['f1']).toBe('@startuml');
		expect(useModelingStore.getState().hasDiagram['f1']).toBe(true);
	});

	it('getDiagram no marca hasDiagram cuando el contenido está vacío', async () => {
		// Arrange
		api.getDiagram.mockResolvedValue({
			id: 'd1',
			feature_id: 'f1',
			diagram_syntax: '',
			created_at: '',
			updated_at: '',
		});

		// Act
		await useModelingStore.getState().getDiagram('prj_01', 'f1');

		// Assert
		expect(useModelingStore.getState().hasDiagram['f1']).toBeUndefined();
	});

	it('generatePlantUmlDiagram guarda el diagrama generado', async () => {
		// Arrange
		api.generatePlantUmlDiagram.mockResolvedValue({
			id: 'd1',
			feature_id: 'f1',
			diagram_syntax: '@startuml generado',
			created_at: '',
			updated_at: '',
		});

		// Act
		const content = await useModelingStore.getState().generatePlantUmlDiagram('prj_01', 'f1');

		// Assert
		expect(content).toBe('@startuml generado');
		expect(useModelingStore.getState().hasDiagram['f1']).toBe(true);
	});

	it('deleteDiagram limpia el contenido y el flag del feature', async () => {
		// Arrange
		useModelingStore.getState().setCurrentDiagrams('f1', 'algo');
		useModelingStore.getState().setHasDiagram('f1', true);
		api.deleteDiagram.mockResolvedValue(undefined);

		// Act
		await useModelingStore.getState().deleteDiagram('prj_01', 'f1');

		// Assert
		const state = useModelingStore.getState();
		expect(state.currentDiagrams['f1']).toBeUndefined();
		expect(state.hasDiagram['f1']).toBeUndefined();
	});

	it('setHasDiagram y resetModeling funcionan correctamente', () => {
		// Act
		useModelingStore.getState().setHasDiagram('f1', true);
		expect(useModelingStore.getState().hasDiagram['f1']).toBe(true);

		useModelingStore.getState().resetModeling();

		// Assert
		expect(useModelingStore.getState().hasDiagram).toEqual({});
		expect(useModelingStore.getState().currentDiagrams).toEqual({});
	});

	it('clearModelingStore limpia el storage persistido y el estado', () => {
		// Arrange
		useModelingStore.getState().setCurrentDiagrams('f1', 'algo');

		// Act
		clearModelingStore();

		// Assert
		expect(useModelingStore.getState().currentDiagrams).toEqual({});
	});
});
