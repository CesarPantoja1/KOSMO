import { create } from 'zustand';
import { USE_MOCKS } from '@/shared/api/config';
import { apiClient } from '@/shared/api';
import type { DiscoveryResponse } from './types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock implementations ---

let mockContent =
	'## Visión del producto\n\nEste es un descubrimiento de prueba en modo mock.';

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

// --- Real API implementations ---

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

// --- Store ---

interface DiscoveryStore {
	currentDiscovery: DiscoveryResponse | null;
	setCurrentDiscovery: (discovery: DiscoveryResponse) => void;
	clearDiscovery: () => void;
	getDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	saveDiscovery: (projectId: string, content: string) => Promise<DiscoveryResponse>;
	generateDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	refineDiscovery: (projectId: string, instructions: string) => Promise<DiscoveryResponse>;
}

export const useDiscoveryStore = create<DiscoveryStore>()((set) => ({
	currentDiscovery: null,
	setCurrentDiscovery: (discovery) => set({ currentDiscovery: discovery }),
	clearDiscovery: () => set({ currentDiscovery: null }),

	getDiscovery: async (projectId) => {
		const data = USE_MOCKS
			? await mockGetDiscovery(projectId)
			: await realGetDiscovery(projectId);
		set({ currentDiscovery: data });
		return data;
	},

	saveDiscovery: async (projectId, content) => {
		const data = USE_MOCKS
			? await mockSaveDiscovery(projectId, content)
			: await realSaveDiscovery(projectId, content);
		set({ currentDiscovery: data });
		return data;
	},

	generateDiscovery: async (projectId) => {
		const data = USE_MOCKS
			? await mockGenerateDiscovery(projectId)
			: await realGenerateDiscovery(projectId);
		set({ currentDiscovery: data });
		return data;
	},

	refineDiscovery: async (projectId, instructions) => {
		const data = USE_MOCKS
			? await mockRefineDiscovery(projectId, instructions)
			: await realRefineDiscovery(projectId, instructions);
		set({ currentDiscovery: data });
		return data;
	},
}));