import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { DiscoveryChatResponse, DiscoveryResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---

let mockContent =
	'## Visión del producto\n\nEste es un descubrimiento de prueba en modo mock.';

const mockChatResponses: DiscoveryChatResponse[] = [
	{
		id: 'mock-chat-1',
		role: 'assistant',
		content: 'Hola, ¿en qué puedo ayudarte con el descubrimiento?',
		created_at: new Date().toISOString(),
		change_suggestions: null,
	},
	{
		id: 'mock-chat-2',
		role: 'assistant',
		content:
			'Aquí tienes una sugerencia de cambio para mejorar la sección de visión del producto.',
		created_at: new Date().toISOString(),
		change_suggestions: [
			{
				id: 'mock-change-1',
				section: 'Visión del producto',
				description: 'Refinar la visión del producto para mayor claridad.',
				diff_before: 'Este es un descubrimiento de prueba en modo mock.',
				diff_after:
					'Este es un descubrimiento refinado con mejoras en la visión del producto.',
				rationale: 'Se mejoró la claridad y el enfoque de la visión del producto.',
			},
		],
	},
];

// --- Mock implementations ---

const mockGetDiscovery = async (projectId: string): Promise<DiscoveryResponse> => {
	await delay(5000);
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
	_instructions: string,
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

const mockSendChatMessage = async (
	_projectId: string,
	_content: string,
): Promise<DiscoveryChatResponse> => {
	await delay(500);
	return mockChatResponses[Math.floor(Math.random() * mockChatResponses.length)];
};

// --- Real implementations ---

const realGetDiscovery = (projectId: string) => {
	return apiClient<DiscoveryResponse>(
		`/api/v1/projects/${projectId}/discovery?_t=${Date.now()}`,
		{
			method: 'GET',
		},
	);
};

const realSaveDiscovery = (projectId: string, content: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
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
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ instructions }),
	});
};

const realSendChatMessage = (projectId: string, content: string) => {
	return apiClient<DiscoveryChatResponse>(
		`/api/v1/projects/${projectId}/discovery/chat`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ content }),
		},
	);
};

// --- Exports (switch based on USE_MOCKS) ---

export const getDiscovery = (projectId: string): Promise<DiscoveryResponse> =>
	USE_MOCKS ? mockGetDiscovery(projectId) : realGetDiscovery(projectId);

export const saveDiscovery = (
	projectId: string,
	content: string,
): Promise<DiscoveryResponse> =>
	USE_MOCKS
		? mockSaveDiscovery(projectId, content)
		: realSaveDiscovery(projectId, content);

export const generateDiscovery = (projectId: string): Promise<DiscoveryResponse> =>
	USE_MOCKS ? mockGenerateDiscovery(projectId) : realGenerateDiscovery(projectId);

export const refineDiscovery = (
	projectId: string,
	instructions: string,
): Promise<DiscoveryResponse> =>
	USE_MOCKS
		? mockRefineDiscovery(projectId, instructions)
		: realRefineDiscovery(projectId, instructions);

export const sendChatMessage = (
	projectId: string,
	content: string,
): Promise<DiscoveryChatResponse> =>
	USE_MOCKS
		? mockSendChatMessage(projectId, content)
		: realSendChatMessage(projectId, content);
