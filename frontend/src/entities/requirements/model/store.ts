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
	loadChatHistory: (requirementId: string) => Promise<RequirementChatResponse[]>;
	sendChatMessage: (
		requirementId: string,
		content: string,
	) => Promise<RequirementChatResponse>;
	clearChatHistory: (requirementId: string) => void;
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
			loadChatHistory: async (requirementId) => {
				const history = await getRequirementChatHistory(requirementId);
				set((state) => ({
					chatHistories: { ...state.chatHistories, [requirementId]: history },
				}));
				return history;
			},
			sendChatMessage: async (requirementId, content) => {
				const userMessage: RequirementChatResponse = {
					id: crypto.randomUUID(),
					role: 'user',
					content,
					created_at: new Date().toISOString(),
				};

				const current = get().chatHistories[requirementId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[requirementId]: [...current, userMessage],
					},
				});

				try {
					const response = await sendRequirementChatMessageApi(requirementId, content);
					const afterUser = get().chatHistories[requirementId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[requirementId]: [...afterUser, response],
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

					const afterUser = get().chatHistories[requirementId] ?? [];
					set({
						chatHistories: {
							...get().chatHistories,
							[requirementId]: [...afterUser, errorMessage],
						},
					});
					throw error;
				}
			},
			clearChatHistory: (requirementId) =>
				set((state) => ({
					chatHistories: { ...state.chatHistories, [requirementId]: [] },
				})),
		}),
		{
			name: 'kosmo-requirements-store',
			partialize: (state) => ({ hasRequirements: state.hasRequirements }),
		},
	),
);

