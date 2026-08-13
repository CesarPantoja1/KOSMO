import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	getRequirementChatHistory,
	getRequirements as getRequirementsApi,
	saveRequirements as saveRequirementsApi,
	generateRequirements as generateRequirementsApi,
	sendRequirementChatMessage as sendRequirementChatMessageApi,
} from '../api/api';
import type { RequirementChatResponse } from './types';

interface RequirementsStore {
	currentRequirements: Record<string, string>;
	setCurrentRequirements: (featureId: string, content: string) => void;
	getRequirements: (projectId: string, featureId: string) => Promise<string>;
	saveRequirements: (projectId: string, featureId: string, content: string) => Promise<void>;
	generateRequirements: (
		projectId: string,
		featureId: string,
	) => Promise<string>;

	hasRequirements: Record<string, boolean>;
	setHasRequirements: (id: string, has: boolean) => void;
	resetRequirements: () => void;

	chatHistories: Record<string, RequirementChatResponse[]>;
	loadChatHistory: (featureId: string) => Promise<RequirementChatResponse[]>;
	sendChatMessage: (
		featureId: string,
		content: string,
	) => Promise<RequirementChatResponse>;
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
			loadChatHistory: async (featureId) => {
				const response = await getRequirementChatHistory(featureId);
				const history = Array.isArray(response) ? response : [];
				set((state) => ({
					chatHistories: { ...state.chatHistories, [featureId]: history },
				}));
				return history;
			},
			sendChatMessage: async (featureId, content) => {
				const userMessage: RequirementChatResponse = {
					id: crypto.randomUUID(),
					role: 'user',
					content,
					created_at: new Date().toISOString(),
				};

				const current = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: [...current, userMessage],
					},
				});

				try {
					const response = await sendRequirementChatMessageApi(featureId, content);
					const afterUser = get().chatHistories[featureId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[featureId]: [...afterUser, response],
						},
					});
					return response;
				} catch (error) {
					// Handle invalid format error or general errors gracefully
					const isInvalidFormat =
						error instanceof Error &&
						(error.message.includes('inválido') || error.message.includes('format'));

					const errorMessage: RequirementChatResponse = {
						id: crypto.randomUUID(),
						role: 'assistant',
						content: isInvalidFormat
							? '⚠️ El agente generó una respuesta con formato inválido. Por favor, intenta reformular tu solicitud.'
							: '⚠️ Ocurrió un error al procesar tu solicitud.',
						created_at: new Date().toISOString(),
						is_invalid_format: isInvalidFormat,
					};

					const afterUser = get().chatHistories[featureId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[featureId]: [...afterUser, errorMessage],
						},
					});
					throw error;
				}
			},
			clearChatHistory: (featureId) =>
				set((state) => ({
					chatHistories: { ...state.chatHistories, [featureId]: [] },
				})),
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
	useRequirementsStore.setState({ hasRequirements: {}, currentRequirements: {}, chatHistories: {} });
};
