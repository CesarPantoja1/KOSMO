import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { RequirementsResponse } from '../model/types';
import type { ChatHistory, ChatMessage, ChatResponse } from '@/entities/chat';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---
// One entry per characteristic (matches IDs from characteristic mock data)

const mockStore: RequirementsResponse[] = [
	{
		feature_id: '1',
		feature_number: 1,
		document_markdown: '## EARS Mock Requirements\n\n',
		total: 5,
	},
];

// --- Mock implementations ---

const mockGetRequirements = async (
	_projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> => {
	await delay(400);
	const found = mockStore.find((c) => c.feature_id === characteristicId);
	return {
		feature_id: characteristicId,
		feature_number: found?.feature_number ?? 0,
		document_markdown: found?.document_markdown ?? '',
		total: 0,
	};
};

const mockSaveRequirements = async (
	_projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await delay(500);
	const idx = mockStore.findIndex((c) => c.feature_id === characteristicId);
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], document_markdown: content };
	}
};

const mockGenerateRequirements = async (
	_projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> => {
	await delay(2000);
	const generated =
		'## EARS Requirements\n\n' +
		'**Ubiquitous**\n' +
		'- The system shall always log every create, update, and delete operation with timestamp and user ID.\n' +
		'- The system shall always ensure data consistency across all related entities.\n\n' +
		'**State-driven**\n' +
		'- While the module is active, the system shall validate all input data against business rules before persisting.\n\n' +
		'**Event-driven**\n' +
		'- When a user triggers a data export, the system shall generate the file in the requested format within 5 seconds.\n\n' +
		'**Unwanted behaviour**\n' +
		'- If a network timeout occurs during a write operation, the system shall roll back the transaction and notify the user.';

	const idx = mockStore.findIndex((c) => c.feature_id === characteristicId);
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], document_markdown: generated };
	}

	return {
		feature_id: characteristicId,
		feature_number: mockStore[idx]?.feature_number ?? 0,
		document_markdown: generated,
		total: 4,
	};
};

const mockDeleteRequirements = async (
	_projectId: string,
	characteristicId: string,
): Promise<void> => {
	await delay(400);
	const idx = mockStore.findIndex((c) => c.feature_id === characteristicId);
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], document_markdown: '', total: 0 };
	}
};

// --- Real implementations ---

const realGetRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> => {
	return apiClient<RequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements?project_id=${encodeURIComponent(projectId)}`,
		{ method: 'GET' },
	);
};

const realSaveRequirements = async (
	projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await apiClient<{ feature_id: string; message: string }>(
		`/api/v1/features/${characteristicId}/requirements`,
		{
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId, markdown: content }),
		},
	);
};

const realGenerateRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> => {
	return apiClient<RequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements/generate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId }),
		},
	);
};

const realDeleteRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<void> => {
	await apiClient<void>(
		`/api/v1/features/${characteristicId}/requirements?project_id=${encodeURIComponent(projectId)}`,
		{ method: 'DELETE' },
	);
};

// --- Exports (switch based on USE_MOCKS) ---

export const getRequirements = (
	projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> =>
	USE_MOCKS
		? mockGetRequirements(projectId, characteristicId)
		: realGetRequirements(projectId, characteristicId);

export const saveRequirements = (
	projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> =>
	USE_MOCKS
		? mockSaveRequirements(projectId, characteristicId, content)
		: realSaveRequirements(projectId, characteristicId, content);

export const generateRequirements = (
	projectId: string,
	characteristicId: string,
): Promise<RequirementsResponse> =>
	USE_MOCKS
		? mockGenerateRequirements(projectId, characteristicId)
		: realGenerateRequirements(projectId, characteristicId);

export const deleteRequirements = (
	projectId: string,
	characteristicId: string,
): Promise<void> =>
	USE_MOCKS
		? mockDeleteRequirements(projectId, characteristicId)
		: realDeleteRequirements(projectId, characteristicId);

const mockChatHistories: Record<string, ChatMessage[]> = {};

export const getRequirementChatHistory = async (
	featureId: string,
	sessionId: string | null = null,
	before?: string | null,
): Promise<ChatHistory> => {
	if (USE_MOCKS) {
		await delay(300);
		return {
			phase: 'requirements',
			context: featureId,
			messages: mockChatHistories[featureId] ?? [],
			has_more: false,
			next_cursor: null,
		};
	}
	const query = new URLSearchParams();
	if (sessionId) query.set('session_id', sessionId);
	if (before) query.set('before', before);
	const suffix = query.toString() ? `?${query.toString()}` : '';
	return await apiClient<ChatHistory>(
		`/api/v1/features/${featureId}/requirements/chat/history${suffix}`,
		{ method: 'GET' },
	);
};

export const sendRequirementChatMessage = async (
	featureId: string,
	content: string,
): Promise<ChatResponse> => {
	if (USE_MOCKS) {
		return mockSendRequirementChatMessage(featureId, content);
	}

	return await apiClient<ChatResponse>(`/api/v1/features/${featureId}/requirements/chat`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ content }),
	});
};

const mockSendRequirementChatMessage = async (
	requirementId: string,
	content: string,
): Promise<ChatResponse> => {
	await delay(600);

	// Check for testing invalid format simulation
	if (content.toLowerCase().includes('error_formato')) {
		throw new Error('Respuesta del agente en formato inválido');
	}

	const userMessage: ChatMessage = {
		id: crypto.randomUUID(),
		role: 'user',
		content,
		created_at: new Date().toISOString(),
		change_suggestions: null,
		modification: null,
	};

	const history = mockChatHistories[requirementId] ?? [];

	const response: ChatResponse = {
		message: {
			id: crypto.randomUUID(),
			role: 'assistant',
			content:
				'He analizado el requisito. Aquí tienes una propuesta con criterios de aceptación:\n\n' +
				'Escenario: Validación exitosa de datos\n' +
				'  Dado que el usuario tiene permisos de edición\n' +
				'  Cuando envía los datos del formulario completos\n' +
				'  Entonces el sistema guarda la información y muestra un mensaje de éxito\n',
			created_at: new Date().toISOString(),
			change_suggestions: [
				{
					id: crypto.randomUUID(),
					section: 'Agregar escenario de validación de datos',
					description: 'cambio leve',
					diff_before: 'antes era asi ',
					diff_after: 'Ahora es asi',
					rationale: 'Cubre el flujo de validación del formulario.',
					applied: true,
					not_applied_reason: null,
				},
			],
			modification: {
				applied: true,
				modified_section: 'Agregar escenario de validación de datos',
				change_description: 'Se aplicaron los cambios sugeridos.',
				modified_document: null,
				before: null,
				after: null,
				undo_version_id: null,
				clarification_message: null,
			},
		},
		modification: {
			applied: true,
			modified_section: 'Agregar escenario de validación de datos',
			change_description: 'Se aplicaron los cambios sugeridos.',
			modified_document: null,
			before: null,
			after: null,
			undo_version_id: null,
			clarification_message: null,
		},
		redirect: null,
		consistency: null,
	};

	mockChatHistories[requirementId] = [...history, userMessage, response.message];
	return response;
};
