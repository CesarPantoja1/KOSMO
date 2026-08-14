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
import { ChatMessage } from '@/entities/chat';

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
	sendChatMessage: (projectId: string, content: string) => Promise<ChatMessage>;
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
					modification: null,
					redirect: null,
					consistency: null,
				};
				set((state) => ({ chatHistory: [...state.chatHistory, userMessage] }));

				const raw = (await sendChatMessageApi(projectId, content)) as unknown as Record<
					string,
					unknown
				>;
				const response: ChatMessage =
					raw.message !== undefined
						? {
								id: crypto.randomUUID(),
								role: 'assistant',
								content: String(raw.message),
								created_at: new Date().toISOString(),
								modification: null,
								redirect: null,
								consistency: null,
							}
						: (raw as unknown as ChatMessage);
				set((state) => ({ chatHistory: [...state.chatHistory, response] }));
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
