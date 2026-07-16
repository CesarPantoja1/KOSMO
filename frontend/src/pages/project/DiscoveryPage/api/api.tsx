import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { DiscoveryResponse } from '../types/discovery';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const isUsingMocks = () => USE_MOCKS;

let mockContent =
	'## Visión del producto\n\nEste es un descubrimiento de prueba en modo mock.';

//
// MOCK implementations
//

const mockGetDiscovery = async (projectId: string): Promise<DiscoveryResponse> => {
	await delay(800);
	return {
		id: 'mock-discovery-1',
		project_id: projectId,
		content: mockContent,
	};
};

const mockSaveDiscovery = async (
	projectId: string,
	content: string,
): Promise<DiscoveryResponse> => {
	await delay(500);
	mockContent = content;
	return {
		id: 'mock-discovery-1',
		project_id: projectId,
		content,
	};
};

const mockGenerateDiscovery = async (projectId: string): Promise<DiscoveryResponse> => {
	await delay(2000);
	mockContent = '## Visión del producto\n\nDescubrimiento generado en modo mock.';
	return {
		id: 'mock-discovery-1',
		project_id: projectId,
		content: mockContent,
	};
};

const mockRefineDiscovery = async (
	projectId: string,
	instructions: string,
): Promise<DiscoveryResponse> => {
	await delay(1500);
	mockContent =
		mockContent +
		'\n\n## Refinamiento aplicado\n\nContenido refinado basado en las instrucciones proporcionadas.';
	return {
		id: 'mock-discovery-1',
		project_id: projectId,
		content: mockContent,
	};
};

//
// REAL API implementations
//

const realGetDiscovery = (projectId: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'GET',
	});
};

const realSaveDiscovery = (projectId: string, content: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({ content }),
	});
};

const realGenerateDiscovery = (projectId: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'POST',
	});
};

const realRefineDiscovery = (projectId: string, instructions: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery/refine`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({ instructions }),
	});
};

//
// Exported functions (switch based on config)
//

export const getDiscovery = (projectId: string) => {
	return isUsingMocks()
		? mockGetDiscovery(projectId)
		: realGetDiscovery(projectId);
};

export const saveDiscovery = (projectId: string, content: string) => {
	return isUsingMocks()
		? mockSaveDiscovery(projectId, content)
		: realSaveDiscovery(projectId, content);
};

export const generateDiscovery = (projectId: string) => {
	return isUsingMocks()
		? mockGenerateDiscovery(projectId)
		: realGenerateDiscovery(projectId);
};

export const refineDiscovery = (projectId: string, instructions: string) => {
	return isUsingMocks()
		? mockRefineDiscovery(projectId, instructions)
		: realRefineDiscovery(projectId, instructions);
};
