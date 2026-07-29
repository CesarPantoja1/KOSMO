import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { ModelingResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---
// One entry per characteristic (matches IDs from characteristic mock data)

const mockStore: ModelingResponse[] = [
	{
		id: 'mock-diagram-1',
		feature_id: '1',
		diagram_syntax: '',
		created_at: '',
		updated_at: '',
	},
];

const MOCK_DIAGRAM = `@startuml
!theme plain
skinparam backgroundColor transparent

title Diagrama de Componentes

package "Frontend" {
  [UI Components] --> [Store]
  [Store] --> [API Client]
}

package "Backend" {
  [API Gateway] --> [Service Layer]
  [Service Layer] --> [Database]
}

[API Client] --> [API Gateway]
@enduml`;

// --- Mock implementations ---

const mockGetDiagram = async (
	_projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> => {
	await delay(600);
	const found = mockStore.find((d) => d.feature_id === characteristicId);
	return (
		found ?? {
			id: `mock-diagram-${characteristicId}`,
			feature_id: characteristicId,
			diagram_syntax: '',
			created_at: '',
			updated_at: '',
		}
	);
};

const mockGeneratePlantUmlDiagram = async (
	_projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> => {
	await delay(1500);
	const now = new Date().toISOString();
	const idx = mockStore.findIndex((d) => d.feature_id === characteristicId);
	const updated: ModelingResponse = {
		id: idx !== -1 ? mockStore[idx].id : `mock-diagram-${characteristicId}`,
		feature_id: characteristicId,
		diagram_syntax: MOCK_DIAGRAM,
		created_at: idx !== -1 ? mockStore[idx].created_at || now : now,
		updated_at: now,
	};
	if (idx !== -1) {
		mockStore[idx] = updated;
	}
	return updated;
};

// --- Real implementations ---

const realGetDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> => {
	return apiClient<ModelingResponse>(
		`/api/v1/features/${characteristicId}/diagram?project_id=${encodeURIComponent(projectId)}`,
		{ method: 'GET', headers: { 'Content-Type': 'application/json' } },
	);
};

const realGeneratePlantUmlDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> => {
	return apiClient<ModelingResponse>(
		`/api/v1/features/${characteristicId}/diagram/generate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId }),
		},
	);
};

// --- Exports (switch based on USE_MOCKS) ---

export const getDiagram = (
	projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> =>
	USE_MOCKS
		? mockGetDiagram(projectId, characteristicId)
		: realGetDiagram(projectId, characteristicId);

export const generatePlantUmlDiagram = (
	projectId: string,
	characteristicId: string,
): Promise<ModelingResponse> =>
	USE_MOCKS
		? mockGeneratePlantUmlDiagram(projectId, characteristicId)
		: realGeneratePlantUmlDiagram(projectId, characteristicId);
