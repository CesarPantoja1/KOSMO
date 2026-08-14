import { ChatMessage } from '@/entities/chat';
import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { DiscoveryResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---

let mockContent =
	'## Visión del producto\n\nEste es un descubrimiento de prueba en modo mock.';

const mockChatResponses: ChatMessage[] = [
	{
		id: 'mock-chat-1',
		role: 'assistant',
		content: 'Hola, ¿en qué puedo ayudarte con el descubrimiento?',
		created_at: new Date().toISOString(),
		modification: null,
		redirect: null,
		consistency: null,
	},
	{
		id: 'mock-chat-2',
		role: 'assistant',
		content:
			'Aquí tienes una sugerencia de cambio para mejorar la sección de visión del producto.',
		created_at: new Date().toISOString(),
		modification: {
			modified_document: 'Discovery',
			modified_section: 'Visión del producto',
			changes: [
				{
					applied: false,
					change_description: 'Refinar la visión del producto para mayor claridad.',
					before: 'Este es un descubrimiento de prueba en modo mock.',
					after:
						'Este es un descubrimiento refinado con mejoras en la visión del producto.',
				},
			],
			undo_version_id: 'mock-undo-1',
			clarification_message: '',
		},
		redirect: null,
		consistency: null,
	},
	{
		id: 'mock-chat-3',
		role: 'assistant',
		content:
			'Tu descubrimiento parece listo. Te redirijo a la siguiente fase del proceso.',
		created_at: new Date().toISOString(),
		modification: null,
		redirect: {
			target_phase: 'requirements',
			redirect_message: 'El descubrimiento está completo, avanza a requerimientos.',
		},
		consistency: null,
	},
	{
		id: 'mock-chat-4',
		role: 'assistant',
		content:
			'Detecté una posible inconsistencia entre la sección de objetivos y los requerimientos.',
		created_at: new Date().toISOString(),
		modification: null,
		redirect: null,
		consistency: {
			phase: 'discovery',
			artifact_id: 'mock-artifact-1',
			artifact_type: 'discovery',
			artifact_label: 'Visión del producto',
			section: 'Objetivos',
			rationale: 'Los objetivos no están alineados con la visión del producto.',
			diff_suggestion: {},
		},
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
	// mockContent = content;
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
): Promise<ChatMessage> => {
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
	return apiClient<ChatMessage>(`/api/v1/projects/${projectId}/discovery/chat`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ content }),
	});
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
): Promise<ChatMessage> =>
	USE_MOCKS
		? mockSendChatMessage(projectId, content)
		: realSendChatMessage(projectId, content);
