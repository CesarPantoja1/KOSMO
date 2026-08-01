import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	getRequirementChatHistory,
	sendRequirementChatMessage as sendRequirementChatMessageApi,
} from '../api/api';
import type { RequirementChatResponse } from './types';

interface RequirementsStore {
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
			hasRequirements: {},
			setHasRequirements: (id, has) =>
				set((state) => ({
					hasRequirements: { ...state.hasRequirements, [id]: has },
				})),
			resetRequirements: () => set({ hasRequirements: {} }),

			chatHistories: {},
			loadChatHistory: async (featureId) => {
			const response = await getRequirementChatHistory(featureId);
			const history = Array.isArray(response) ? response : (response as any)?.messages ?? [];
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
			partialize: (state) => ({ hasRequirements: state.hasRequirements }),
		},
	),
);

