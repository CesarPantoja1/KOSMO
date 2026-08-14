import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	getRequirementChatHistory,
	getRequirements as getRequirementsApi,
	saveRequirements as saveRequirementsApi,
	generateRequirements as generateRequirementsApi,
	sendRequirementChatMessage as sendRequirementChatMessageApi,
} from '../api/api';
import type { ChatMessage, ChatResponse } from '@/entities/chat';
import {
	appendMessage,
	createAssistantError,
	createUserMessage,
} from '@/entities/chat';

interface RequirementsStore {
	currentRequirements: Record<string, string>;
	setCurrentRequirements: (featureId: string, content: string) => void;
	getRequirements: (projectId: string, featureId: string) => Promise<string>;
	saveRequirements: (
		projectId: string,
		featureId: string,
		content: string,
	) => Promise<void>;
	generateRequirements: (projectId: string, featureId: string) => Promise<string>;

	hasRequirements: Record<string, boolean>;
	setHasRequirements: (id: string, has: boolean) => void;
	resetRequirements: () => void;

	chatHistories: Record<string, ChatMessage[]>;
	loadChatHistory: (
		featureId: string,
		sessionId?: string | null,
	) => Promise<ChatMessage[]>;
	historyHasMore: boolean;
	historyCursor: string | null;
	loadOlderChatHistory: (
		featureId: string,
		sessionId?: string | null,
	) => Promise<void>;
	sendChatMessage: (featureId: string, content: string) => Promise<ChatResponse>;
	appendUserMessage: (featureId: string, content: string) => void;
	appendAssistantMessage: (featureId: string, message: ChatMessage) => void;
	clearChatHistory: (featureId: string) => void;
}

export const useRequirementsStore = create<RequirementsStore>()(
	persist(
		(set, get) => ({
			currentRequirements: {},
			setCurrentRequirements: (featureId, content) =>
				set((state) => ({
					currentRequirements: { ...state.currentRequirements, [featureId]: content },
				})),
			getRequirements: async (projectId, featureId) => {
				const data = await getRequirementsApi(projectId, featureId);
				const content = data.document_markdown;
				if (content) {
					set((state) => ({
						currentRequirements: { ...state.currentRequirements, [featureId]: content },
						hasRequirements: { ...state.hasRequirements, [featureId]: true },
					}));
				}
				return content;
			},
			saveRequirements: async (projectId, featureId, content) => {
				await saveRequirementsApi(projectId, featureId, content);
				set((state) => ({
					currentRequirements: { ...state.currentRequirements, [featureId]: content },
					hasRequirements: { ...state.hasRequirements, [featureId]: true },
				}));
			},
			generateRequirements: async (projectId, featureId) => {
				const data = await generateRequirementsApi(projectId, featureId);
				const content = data.document_markdown;
				set((state) => ({
					currentRequirements: { ...state.currentRequirements, [featureId]: content },
					hasRequirements: { ...state.hasRequirements, [featureId]: true },
				}));
				return content;
			},

			hasRequirements: {},
			setHasRequirements: (id, has) =>
				set((state) => ({
					hasRequirements: { ...state.hasRequirements, [id]: has },
				})),
			resetRequirements: () => set({ hasRequirements: {}, currentRequirements: {} }),

			chatHistories: {},
			historyHasMore: false,
			historyCursor: null,
			loadChatHistory: async (featureId, sessionId = null) => {
				const response = await getRequirementChatHistory(featureId, sessionId);
				const history = response.messages ?? [];
				set((state) => ({
					chatHistories: { ...state.chatHistories, [featureId]: history },
					historyHasMore: response.has_more,
					historyCursor: response.next_cursor,
				}));
				return history;
			},

			loadOlderChatHistory: async (featureId, sessionId = null) => {
				const { historyCursor, chatHistories } = get();
				if (!historyCursor) return;
				const response = await getRequirementChatHistory(
					featureId,
					sessionId,
					historyCursor,
				);
				set((state) => ({
					chatHistories: {
						...state.chatHistories,
						[featureId]: [
							...(response.messages ?? []),
							...(chatHistories[featureId] ?? []),
						],
					},
					historyHasMore: response.has_more,
					historyCursor: response.next_cursor,
				}));
			},
			sendChatMessage: async (featureId, content) => {
				const userMessage = createUserMessage(content);

				const current = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: appendMessage(current, userMessage),
					},
				});

				try {
					const response = await sendRequirementChatMessageApi(featureId, content);
					const afterUser = get().chatHistories[featureId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[featureId]: appendMessage(afterUser, response.message),
						},
					});
					return response;
				} catch (error) {
					// Handle invalid format error or general errors gracefully
					const isInvalidFormat =
						error instanceof Error &&
						(error.message.includes('inválido') || error.message.includes('format'));

					const errorMessage = createAssistantError(
						isInvalidFormat
							? '⚠️ El agente generó una respuesta con formato inválido. Por favor, intenta reformular tu solicitud.'
							: '⚠️ Ocurrió un error al procesar tu solicitud.',
					);

					const afterUser = get().chatHistories[featureId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[featureId]: appendMessage(afterUser, errorMessage),
						},
					});
					throw error;
				}
			},
			clearChatHistory: (featureId) =>
				set((state) => ({
					chatHistories: { ...state.chatHistories, [featureId]: [] },
				})),

			appendUserMessage: (featureId, content) => {
				const current = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: appendMessage(current, createUserMessage(content)),
					},
				});
			},

			appendAssistantMessage: (featureId, message) => {
				const current = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: appendMessage(current, message),
					},
				});
			},
		}),
		{
			name: 'kosmo-requirements-store',
			partialize: (state) => ({
				hasRequirements: state.hasRequirements,
				currentRequirements: state.currentRequirements,
			}),
		},
	),
);

export const clearRequirementsStore = () => {
	useRequirementsStore.persist.clearStorage();
	useRequirementsStore.setState({
		hasRequirements: {},
		currentRequirements: {},
		chatHistories: {},
	});
};
