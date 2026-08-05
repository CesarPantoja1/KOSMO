import { create } from 'zustand';
import {
	generateDiscovery,
	getDiscovery,
	refineDiscovery,
	saveDiscovery,
	sendChatMessage as sendChatMessageApi,
} from '../api/api';
import type { DiscoveryChatResponse, DiscoveryResponse } from './types';

interface DiscoveryStore {
	currentDiscovery: DiscoveryResponse | null;
	chatHistory: DiscoveryChatResponse[];
	setCurrentDiscovery: (discovery: DiscoveryResponse) => void;
	clearDiscovery: () => void;
	clearChatHistory: () => void;
	resetDiscovery: () => void;
	getDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	saveDiscovery: (projectId: string, content: string) => Promise<DiscoveryResponse>;
	generateDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	refineDiscovery: (
		projectId: string,
		instructions: string,
	) => Promise<DiscoveryResponse>;
	sendChatMessage: (projectId: string, content: string) => Promise<DiscoveryChatResponse>;
}

export const useDiscoveryStore = create<DiscoveryStore>()((set, get) => ({
	currentDiscovery: null,
	chatHistory: [],

	setCurrentDiscovery: (discovery) => set({ currentDiscovery: discovery }),
	clearDiscovery: () => set({ currentDiscovery: null }),
	clearChatHistory: () => set({ chatHistory: [] }),
	resetDiscovery: () => set({ currentDiscovery: null, chatHistory: [] }),

	getDiscovery: async (projectId) => {
		const data = await getDiscovery(projectId);
		set({ currentDiscovery: data });
		return data;
	},

	saveDiscovery: async (projectId, content) => {
		const data = await saveDiscovery(projectId, content);
		set({ currentDiscovery: data });
		return data;
	},

	generateDiscovery: async (projectId) => {
		const data = await generateDiscovery(projectId);
		set({ currentDiscovery: data });
		return data;
	},

	refineDiscovery: async (projectId, instructions) => {
		const data = await refineDiscovery(projectId, instructions);
		set({ currentDiscovery: data });
		return data;
	},

	sendChatMessage: async (projectId, content) => {
		const userMessage: DiscoveryChatResponse = {
			id: crypto.randomUUID(),
			role: 'user',
			content,
			created_at: new Date().toISOString(),
		};
		set((state) => ({ chatHistory: [...state.chatHistory, userMessage] }));

		const raw = await sendChatMessageApi(projectId, content) as unknown as Record<string, unknown>;
		const response: DiscoveryChatResponse = raw.message !== undefined
			? {
					id: crypto.randomUUID(),
					role: 'assistant',
					content: String(raw.message),
					created_at: new Date().toISOString(),
				}
			: raw as unknown as DiscoveryChatResponse;
		set((state) => ({ chatHistory: [...state.chatHistory, response] }));
		return response;
	},
}));
