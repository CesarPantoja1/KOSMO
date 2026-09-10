import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { Project, ProjectGitHubStatus, PushGitHubRequest } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock data ---

const mockProjects: Project[] = [
	{
		id: 'mock-project-1',
		name: 'Sistema de Punto de Venta',
		slug: 'sistema-de-punto-de-venta',
		description:
			'Sistema integral para gestión de ventas, inventario y reportes para pequeñas y medianas empresas.',
		owner_id: 'mock-user-1',
		created_at: '2024-01-15T10:00:00Z',
		updated_at: '2024-01-15T10:00:00Z',
		current_phase: 'discovery',
		status: 'active',
	},
	{
		id: 'mock-project-2',
		name: 'App de Gestión de Tareas',
		slug: 'app-de-gestion-de-tareas',
		description:
			'Plataforma colaborativa para la gestión de proyectos y seguimiento de tareas en equipos de trabajo.',
		owner_id: 'mock-user-1',
		created_at: '2024-02-10T09:00:00Z',
		updated_at: '2024-02-10T09:00:00Z',
		current_phase: 'requirements',
		status: 'active',
	},
];

// --- Mock implementations ---

const mockGetProjects = async (): Promise<Project[]> => {
	await delay(600);
	return [...mockProjects];
};

const mockGetProject = async (id: string): Promise<Project> => {
	await delay(400);
	const found = mockProjects.find((p) => p.id === id);
	if (!found) throw new Error(`Mock project not found: ${id}`);
	return { ...found };
};

const mockCreateProject = async (body: {
	name: string;
	description: string;
}): Promise<Project> => {
	await delay(500);
	const newProject: Project = {
		id: `mock-project-${mockProjects.length + 1}`,
		name: body.name,
		slug: body.name.toLowerCase().replace(/\s+/g, '-'),
		description: body.description,
		owner_id: 'mock-user-1',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		current_phase: 'discovery',
		status: 'active',
	};
	mockProjects.push(newProject);
	return { ...newProject };
};

const mockDeleteProject = async (id: string): Promise<void> => {
	await delay(400);
	const index = mockProjects.findIndex((p) => p.id === id);
	if (index === -1) throw new Error(`Mock project not found: ${id}`);
	mockProjects.splice(index, 1);
};

const mockGitHubStatus: Record<string, ProjectGitHubStatus> = {};

const mockGetProjectGitHubStatus = async (id: string): Promise<ProjectGitHubStatus> => {
	await delay(400);
	const found = mockGitHubStatus[id];
	if (found) return { ...found };
	return {
		has_repository: false,
		sync_status: 'not_created',
		suggested_repo_name: `kosmo-${id}`,
		error_message: null,
	};
};

const mockPushToGitHub = async (
	id: string,
	repoName?: string,
): Promise<ProjectGitHubStatus> => {
	await delay(800);
	const name = repoName ?? mockGitHubStatus[id]?.repo_name ?? `kosmo-${id}`;
	mockGitHubStatus[id] = {
		has_repository: true,
		repo_name: name,
		repo_url: `https://github.com/mock-user/${name}`,
		is_public: false,
		last_push_at: new Date().toISOString(),
		last_commit_hash: 'mock-commit-hash',
		sync_status: 'synced',
		suggested_repo_name: name,
		error_message: null,
	};
	return { ...mockGitHubStatus[id] };
};

// --- Real implementations ---

const realGetProjects = (): Promise<Project[]> =>
	apiClient<Project[]>('/api/v1/projects', { method: 'GET' });

const realGetProject = (id: string): Promise<Project> =>
	apiClient<Project>(`/api/v1/projects/${id}`, { method: 'GET' });

export const realCreateProject = (body: { name: string; description: string }) => {
	return apiClient<Project>('/api/v1/projects', {
		method: 'POST',
		body: JSON.stringify(body),
	});
};

const realDeleteProject = (id: string): Promise<void> =>
	apiClient<void>(`/api/v1/projects/${id}`, { method: 'DELETE' });

const realGetProjectGitHubStatus = (id: string): Promise<ProjectGitHubStatus> =>
	apiClient<ProjectGitHubStatus>(`/api/v1/projects/${id}/github`, { method: 'GET' });

const realPushToGitHub = (id: string, body: PushGitHubRequest): Promise<ProjectGitHubStatus> =>
	apiClient<ProjectGitHubStatus>(`/api/v1/projects/${id}/github/push`, {
		method: 'POST',
		body: JSON.stringify(body),
	});

// --- Exports (switch based on USE_MOCKS) ---

export const getProjects = (): Promise<Project[]> =>
	USE_MOCKS ? mockGetProjects() : realGetProjects();

export const getProject = (id: string): Promise<Project> =>
	USE_MOCKS ? mockGetProject(id) : realGetProject(id);

export const createProject = (body: {
	name: string;
	description: string;
}): Promise<Project> => (USE_MOCKS ? mockCreateProject(body) : realCreateProject(body));

export const deleteProject = (id: string): Promise<void> =>
	USE_MOCKS ? mockDeleteProject(id) : realDeleteProject(id);

export const getProjectGitHubStatus = (id: string): Promise<ProjectGitHubStatus> =>
	USE_MOCKS ? mockGetProjectGitHubStatus(id) : realGetProjectGitHubStatus(id);

export const pushProjectToGitHub = (
	id: string,
	body: PushGitHubRequest,
): Promise<ProjectGitHubStatus> =>
	USE_MOCKS
		? mockPushToGitHub(id, body.repo_name ?? undefined)
		: realPushToGitHub(id, body);
