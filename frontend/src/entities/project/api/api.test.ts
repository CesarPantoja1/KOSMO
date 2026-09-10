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

describe('project/api — modo real (USE_MOCKS=false)', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
	});

	it('getProjects consulta la lista de proyectos', async () => {
		// Arrange
		const { getProjects } = await import('./api');
		mockFetchOk([{ id: 'p1', name: 'Proyecto 1' }]);

		// Act
		const result = await getProjects();

		// Assert
		expect(result).toHaveLength(1);
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/projects'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('getProject consulta un proyecto por id', async () => {
		// Arrange
		const { getProject } = await import('./api');
		mockFetchOk({ id: 'p1', name: 'Proyecto 1' });

		// Act
		const result = await getProject('p1');

		// Assert
		expect(result.name).toBe('Proyecto 1');
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/projects/p1'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('createProject hace POST con nombre y descripción', async () => {
		// Arrange
		const { createProject } = await import('./api');
		mockFetchOk({ id: 'p1', name: 'Nuevo' });

		// Act
		await createProject({ name: 'Nuevo', description: 'desc' });

		// Assert
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/projects');
		expect((options as RequestInit).method).toBe('POST');
		expect(JSON.parse((options as RequestInit).body as string)).toEqual({
			name: 'Nuevo',
			description: 'desc',
		});
	});

	it('deleteProject hace DELETE al proyecto', async () => {
		// Arrange
		const { deleteProject } = await import('./api');
		mockFetchOk(null);

		// Act
		await deleteProject('p1');

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/projects/p1'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('getProjectGitHubStatus consulta el estado de GitHub del proyecto', async () => {
		// Arrange
		const { getProjectGitHubStatus } = await import('./api');
		mockFetchOk({ has_repository: false, sync_status: 'not_created' });

		// Act
		await getProjectGitHubStatus('p1');

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/projects/p1/github'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('pushProjectToGitHub hace POST con el cuerpo de la petición', async () => {
		// Arrange
		const { pushProjectToGitHub } = await import('./api');
		mockFetchOk({ has_repository: true, sync_status: 'synced' });

		// Act
		await pushProjectToGitHub('p1', { repo_name: 'mi-repo', is_public: true });

		// Assert
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/projects/p1/github/push');
		expect(JSON.parse((options as RequestInit).body as string)).toEqual({
			repo_name: 'mi-repo',
			is_public: true,
		});
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		const { getProjects } = await import('./api');
		mockFetchError(500, { detail: 'Error interno' });

		// Act & Assert
		await expect(getProjects()).rejects.toThrow('Error interno');
	});
});

describe('project/api — modo mock (USE_MOCKS=true)', () => {
	beforeEach(() => {
		vi.resetModules();
		vi.doMock('@/shared/api/config', () => ({ USE_MOCKS: true }));
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('getProjects resuelve la lista mock de proyectos', async () => {
		// Arrange
		const { getProjects } = await import('./api');

		// Act
		const promise = getProjects();
		await vi.advanceTimersByTimeAsync(600);
		const result = await promise;

		// Assert
		expect(result.length).toBeGreaterThan(0);
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it('getProject lanza error si el id mock no existe', async () => {
		// Arrange
		const { getProject } = await import('./api');

		// Act
		const promise = getProject('no-existe');
		const assertion = expect(promise).rejects.toThrow('Mock project not found');
		await vi.advanceTimersByTimeAsync(400);

		// Assert
		await assertion;
	});

	it('createProject agrega un nuevo proyecto mock', async () => {
		// Arrange
		const { createProject } = await import('./api');

		// Act
		const promise = createProject({ name: 'Mi Proyecto', description: 'd' });
		await vi.advanceTimersByTimeAsync(500);
		const result = await promise;

		// Assert
		expect(result.name).toBe('Mi Proyecto');
		expect(result.slug).toBe('mi-proyecto');
	});

	it('deleteProject lanza error si el id mock no existe', async () => {
		// Arrange
		const { deleteProject } = await import('./api');

		// Act
		const promise = deleteProject('no-existe');
		const assertion = expect(promise).rejects.toThrow('Mock project not found');
		await vi.advanceTimersByTimeAsync(400);

		// Assert
		await assertion;
	});

	it('getProjectGitHubStatus devuelve not_created cuando no hay estado previo', async () => {
		// Arrange
		const { getProjectGitHubStatus } = await import('./api');

		// Act
		const promise = getProjectGitHubStatus('p-nuevo');
		await vi.advanceTimersByTimeAsync(400);
		const result = await promise;

		// Assert
		expect(result.sync_status).toBe('not_created');
	});

	it('pushProjectToGitHub marca el repo como sincronizado', async () => {
		// Arrange
		const { pushProjectToGitHub } = await import('./api');

		// Act
		const promise = pushProjectToGitHub('p1', { repo_name: 'mi-repo', is_public: true });
		await vi.advanceTimersByTimeAsync(800);
		const result = await promise;

		// Assert
		expect(result.sync_status).toBe('synced');
		expect(result.repo_name).toBe('mi-repo');
	});
});
