import { create } from 'zustand';
import type { DiscoveryChatResponse, DiscoveryResponse } from './types';
import {
	getDiscovery,
	saveDiscovery,
	generateDiscovery,
	refineDiscovery,
	sendChatMessage as sendChatMessageApi,
} from '../api/api';

interface DiscoveryStore {
	currentDiscovery: DiscoveryResponse | null;
	chatHistory: DiscoveryChatResponse[];
	setCurrentDiscovery: (discovery: DiscoveryResponse) => void;
	clearDiscovery: () => void;
	clearChatHistory: () => void;
	getDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	saveDiscovery: (projectId: string, content: string) => Promise<DiscoveryResponse>;
	generateDiscovery: (projectId: string) => Promise<DiscoveryResponse>;
	refineDiscovery: (projectId: string, instructions: string) => Promise<DiscoveryResponse>;
	sendChatMessage: (projectId: string, content: string) => Promise<DiscoveryChatResponse>;
}

export const useDiscoveryStore = create<DiscoveryStore>()((set, get) => ({
	currentDiscovery: null,
	chatHistory: [],

	setCurrentDiscovery: (discovery) => set({ currentDiscovery: discovery }),
	clearDiscovery: () => set({ currentDiscovery: null }),
	clearChatHistory: () => set({ chatHistory: [] }),

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
			create_at: new Date().toISOString(),
		};
		set({ chatHistory: [...get().chatHistory, userMessage] });

		const response = await sendChatMessageApi(projectId, content);
		set({ chatHistory: [...get().chatHistory, response] });
		return response;
	},
}));
