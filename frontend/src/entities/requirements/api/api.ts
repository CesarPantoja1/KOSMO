import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { RequirementChatResponse, RequirementsResponse } from '../model/types';


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

const mockChatHistories: Record<string, RequirementChatResponse[]> = {};

export const getRequirementChatHistory = async (
	featureId: string,
): Promise<RequirementChatResponse[]> => {
	if (USE_MOCKS) {
		await delay(300);
		return mockChatHistories[featureId] ?? [];
	}
	return await apiClient<RequirementChatResponse[]>(
		`/api/v1/features/${featureId}/requirements/chat/history`,
		{ method: 'GET' },
	);
};

export const sendRequirementChatMessage = async (
	featureId: string,
	content: string,
): Promise<RequirementChatResponse> => {
	if (USE_MOCKS) {
		return mockSendRequirementChatMessage(featureId, content);
	}

	return await apiClient<RequirementChatResponse>(
		`/api/v1/features/${featureId}/requirements/chat`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ content }),
		},
	);
};

const mockSendRequirementChatMessage = async (
	requirementId: string,
	content: string,
): Promise<RequirementChatResponse> => {
	await delay(600);

	// Check for testing invalid format simulation
	if (content.toLowerCase().includes('error_formato')) {
		throw new Error('Respuesta del agente en formato inválido');
	}

	const userMessage: RequirementChatResponse = {
		id: crypto.randomUUID(),
		role: 'user',
		content,
		created_at: new Date().toISOString(),
	};

	const history = mockChatHistories[requirementId] ?? [];

	const isModification =
		history.length > 0 ||
		content.toLowerCase().includes('modificar') ||
		content.toLowerCase().includes('cambiar') ||
		content.toLowerCase().includes('anterior') ||
		content.toLowerCase().includes('diff');

	const diff_before = isModification
		? 'Escenario: Validación antigua de datos\n' +
		  '  Dado que el usuario no tiene verificación\n' +
		  '  Cuando envía los datos incompletos\n' +
		  '  Entonces el sistema genera un error genérico\n'
		: 'No especificado';

	const response: RequirementChatResponse = {
		id: crypto.randomUUID(),
		role: 'assistant',
		content:
			'He analizado el requisito. Aquí tienes una propuesta con criterios de aceptación:\n\n' +
			'Escenario: Validación exitosa de datos\n' +
			'  Dado que el usuario tiene permisos de edición\n' +
			'  Cuando envía los datos del formulario completos\n' +
			'  Entonces el sistema guarda la información y muestra un mensaje de éxito\n',
		created_at: new Date().toISOString(),
		change_suggestion: {
			id: crypto.randomUUID(),
			section: 'Criterios de Aceptación',
			description: isModification
				? 'Actualizar escenario de validación'
				: 'Agregar escenario de validación de datos',
			diff_before,
			diff_after:
				'Escenario: Validación exitosa\n' +
				'  Dado que el usuario está autenticado\n' +
				'  Cuando completa la acción\n' +
				'  Entonces se confirma la operación\n',
			rationale: 'Mejora la precisión de los criterios de aceptación EARS.',
		},
	};

	mockChatHistories[requirementId] = [...history, userMessage, response];
	return response;
};


