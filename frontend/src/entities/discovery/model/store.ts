import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	generateDiscovery,
	getDiscovery,
	refineDiscovery,
	saveDiscovery,
	sendChatMessage as sendChatMessageApi,
} from '../api/api';
import type { DiscoveryResponse } from './types';
import type { ChatMessage, ChatResponse } from '@/entities/chat';

interface DiscoveryStore {
	currentDiscovery: DiscoveryResponse | null;
	chatHistory: ChatMessage[];
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
	sendChatMessage: (projectId: string, content: string) => Promise<ChatResponse>;
}

export const useDiscoveryStore = create<DiscoveryStore>()(
	persist(
		(set, _get) => ({
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
				const userMessage: ChatMessage = {
					id: crypto.randomUUID(),
					role: 'user',
					content,
					created_at: new Date().toISOString(),
					change_suggestions: null,
					modification: null,
				};
				set((state) => ({ chatHistory: [...state.chatHistory, userMessage] }));

				const response = await sendChatMessageApi(projectId, content);
				set((state) => ({ chatHistory: [...state.chatHistory, response.message] }));
				return response;
			},
		}),
		{
			name: 'kosmo-discovery-store',
			partialize: (state) => ({
				currentDiscovery: state.currentDiscovery,
				chatHistory: state.chatHistory,
			}),
		},
	),
);

export const clearDiscoveryStore = () => {
	useDiscoveryStore.persist.clearStorage();
	useDiscoveryStore.setState({ currentDiscovery: null, chatHistory: [] });
};
