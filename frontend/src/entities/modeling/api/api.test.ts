import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();

function mockFetchOk(body: unknown) {
	fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => body });
}

function mockFetchError(status: number, body: unknown) {
	fetchMock.mockResolvedValue({
		ok: false,
		status,
		headers: new Headers(),
		json: async () => body,
	});
}

afterEach(() => {
	fetchMock.mockReset();
	vi.unstubAllGlobals();
	vi.resetModules();
	vi.doUnmock('@/shared/api/config');
});

describe('modeling/api — modo real (USE_MOCKS=false)', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
	});

	it('getDiagram consulta el endpoint con project_id como query', async () => {
		// Arrange
		const { getDiagram } = await import('./api');
		mockFetchOk({ id: 'd1', feature_id: 'f1', diagram_syntax: '@startuml' });

		// Act
		const result = await getDiagram('prj_01', 'f1');

		// Assert
		expect(result.diagram_syntax).toBe('@startuml');
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/features/f1/diagram?project_id=prj_01'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('generatePlantUmlDiagram hace POST con project_id', async () => {
		// Arrange
		const { generatePlantUmlDiagram } = await import('./api');
		mockFetchOk({ id: 'd1', feature_id: 'f1', diagram_syntax: 'generado' });

		// Act
		const result = await generatePlantUmlDiagram('prj_01', 'f1');

		// Assert
		expect(result.diagram_syntax).toBe('generado');
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/features/f1/diagram/generate'),
			expect.objectContaining({ method: 'POST' }),
		);
	});

	it('deleteDiagram hace DELETE con project_id como query', async () => {
		// Arrange
		const { deleteDiagram } = await import('./api');
		mockFetchOk(null);

		// Act
		await deleteDiagram('prj_01', 'f1');

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/features/f1/diagram?project_id=prj_01'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		const { getDiagram } = await import('./api');
		mockFetchError(500, { detail: 'Error interno' });

		// Act & Assert
		await expect(getDiagram('prj_01', 'f1')).rejects.toThrow('Error interno');
	});
});

describe('modeling/api — modo mock (USE_MOCKS=true)', () => {
	beforeEach(() => {
		vi.resetModules();
		vi.doMock('@/shared/api/config', () => ({ USE_MOCKS: true }));
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('getDiagram resuelve el diagrama mock existente', async () => {
		// Arrange
		const { getDiagram } = await import('./api');

		// Act
		const promise = getDiagram('prj_01', '1');
		await vi.advanceTimersByTimeAsync(600);
		const result = await promise;

		// Assert
		expect(result.feature_id).toBe('1');
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it('generatePlantUmlDiagram genera un diagrama con sintaxis PlantUML', async () => {
		// Arrange
		const { generatePlantUmlDiagram } = await import('./api');

		// Act
		const promise = generatePlantUmlDiagram('prj_01', '1');
		await vi.advanceTimersByTimeAsync(1500);
		const result = await promise;

		// Assert
		expect(result.diagram_syntax).toContain('@startuml');
	});

	it('deleteDiagram no lanza error en modo mock', async () => {
		// Arrange
		const { deleteDiagram } = await import('./api');

		// Act
		const promise = deleteDiagram('prj_01', '1');
		await vi.advanceTimersByTimeAsync(400);

		// Assert
		await expect(promise).resolves.toBeUndefined();
	});
});
