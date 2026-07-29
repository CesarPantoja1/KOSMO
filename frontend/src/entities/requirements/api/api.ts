import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import { RequirementsResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

//
// MOCK implementations
//

const mockSaveRequirements = async (
	_projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await delay(500);
	const idx = mockStore.findIndex((c) => c.id === characteristicId);
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], requirements: content };
	}
};

const mockGenerateRequirements = async (
	_projectId: string,
	_characteristicId: string,
): Promise<string> => {
	await delay(2000);
	return (
		'## EARS Requirements\n\n' +
		'**Ubiquitous**\n' +
		'- The system shall always log every create, update, and delete operation with timestamp and user ID.\n' +
		'- The system shall always ensure data consistency across all related entities.\n\n' +
		'**State-driven**\n' +
		'- While the module is active, the system shall validate all input data against business rules before persisting.\n\n' +
		'**Event-driven**\n' +
		'- When a user triggers a data export, the system shall generate the file in the requested format within 5 seconds.\n\n' +
		'**Unwanted behaviour**\n' +
		'- If a network timeout occurs during a write operation, the system shall roll back the transaction and notify the user.'
	);
};

const mockGetRequirements = async (
	_projectId: string,
	characteristicId: string,
): Promise<string> => {
	await delay(400);
	const found = mockStore.find((c) => c.id === characteristicId);
	return found?.requirements ?? '';
};

const mockRefineRequirements = async (
	_projectId: string,
	characteristicId: string,
	instructions: string,
): Promise<RequirementsResponse> => {
	await delay(1500);
	const idx = mockStore.findIndex((c) => c.id === characteristicId);
	const newRequirements =
		(mockStore[idx]?.requirements || '') + `\n\n*Refinado con IA: ${instructions}*`;
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], requirements: newRequirements };
	}
	return {
		feature_id: characteristicId,
		feature_number: mockStore[idx]?.number ?? 0,
		requirements_markdown: newRequirements,
		total: 10,
	};
};

//
// REAL API implementations
//

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
): Promise<string> => {
	const data = await apiClient<RequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements/generate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId }),
		},
	);
	return data.requirements_markdown;
};

interface GetRequirementsResponse {
	document_markdown: string;
}

const realGetRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	const data = await apiClient<GetRequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements?project_id=${encodeURIComponent(projectId)}`,
		{ method: 'GET' },
	);
	return data.document_markdown;
};

const realRefineRequirements = async (
	projectId: string,
	characteristicId: string,
	instructions: string,
): Promise<RequirementsResponse> => {
	const data = await apiClient<RequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements/refine`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId, instructions }),
		},
	);
	return data;
};

//
// Exported functions (switch based on config)
//

const isUsingMocks = () => USE_MOCKS;

export const saveRequirements = async (
	projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	return isUsingMocks()
		? mockSaveRequirements(projectId, characteristicId, content)
		: realSaveRequirements(projectId, characteristicId, content);
};

export const generateRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGenerateRequirements(projectId, characteristicId)
		: realGenerateRequirements(projectId, characteristicId);
};

export const getRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGetRequirements(projectId, characteristicId)
		: realGetRequirements(projectId, characteristicId);
};

export const refineRequirements = async (
	projectId: string,
	characteristicId: string,
	instructions: string,
): Promise<RequirementsResponse> => {
	return isUsingMocks()
		? mockRefineRequirements(projectId, characteristicId, instructions)
		: realRefineRequirements(projectId, characteristicId, instructions);
};
