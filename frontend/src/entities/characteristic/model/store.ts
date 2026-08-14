import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	addCharacteristic,
	generateCharacteristics,
	getCharacteristics,
	getSuggestCharacteristics,
	sendChatMessage,
} from '../api/api';
import type {
	CharacteristicResponse,
	CreateCharacteristicResponse,
	SuggestCharacteristic,
} from './types';
import { ChatMessage } from '@/entities/chat';

interface CharacteristicStore {
	currentCharacteristics: CharacteristicResponse[];
	chatHistories: Record<string, ChatMessage[]>;
	setCurrentCharacteristics: (characteristics: CharacteristicResponse[]) => void;
	currentSuggestions: SuggestCharacteristic[];
	setCurrentSuggestions: (suggestions: SuggestCharacteristic[]) => void;
	clearCharacteristics: () => void;
	clearChatHistory: (featureId: string) => void;
	clearAllChatHistories: () => void;
	getCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	generateCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	getSuggestCharacteristics: (projectId: string) => Promise<SuggestCharacteristic[]>;
	addCharacteristic: (
		projectId: string,
		item: { title: string; description: string; origin?: string; force?: boolean },
	) => Promise<CreateCharacteristicResponse>;

	sendChatMessage: (featureId: string, content: string) => Promise<ChatMessage>;

	selectedId: string | null;
	setSelectedId: (id: string | null) => void;
}

export const useCharacteristicStore = create<CharacteristicStore>()(
	persist(
		(set, get) => ({
			currentCharacteristics: [],
			setCurrentCharacteristics: (characteristics) =>
				set({ currentCharacteristics: characteristics }),
			currentSuggestions: [],
			setCurrentSuggestions: (suggestions) => set({ currentSuggestions: suggestions }),
			clearCharacteristics: () =>
				set({ currentCharacteristics: [], currentSuggestions: [], selectedId: null }),

			chatHistories: {},
			clearChatHistory: (featureId) => {
				const { chatHistories } = get();
				set({ chatHistories: { ...chatHistories, [featureId]: [] } });
			},
			clearAllChatHistories: () => set({ chatHistories: {} }),

			getCharacteristics: async (projectId) => {
				const data = await getCharacteristics(projectId);
				set({ currentCharacteristics: data });
				return data;
			},

			generateCharacteristics: async (projectId) => {
				const data = await generateCharacteristics(projectId);
				set({ currentCharacteristics: data });
				return data;
			},

			getSuggestCharacteristics: async (projectId) => {
				const data = await getSuggestCharacteristics(projectId);
				set({ currentSuggestions: data });
				return data;
			},

			addCharacteristic: async (projectId, item) => {
				const data = await addCharacteristic(projectId, item);
				const feat = data.feature;
				if (data.is_saved && feat) {
					set((state) => ({
						currentCharacteristics: [...state.currentCharacteristics, feat],
					}));
				}
				return data;
			},

			sendChatMessage: async (featureId, content) => {
				const userMessage: ChatMessage = {
					id: crypto.randomUUID(),
					role: 'user',
					content,
					created_at: new Date().toISOString(),
					modification: null,
					redirect: null,
					consistency: null,
				};

				const current = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: [...current, userMessage],
					},
				});

				const response = await sendChatMessage(featureId, content);

				const afterUser = get().chatHistories[featureId] ?? [];
				set({
					chatHistories: {
						...get().chatHistories,
						[featureId]: [...afterUser, response],
					},
				});

				return response;
			},

			selectedId: null,
			setSelectedId: (id) => set({ selectedId: id }),
		}),
		{
			name: 'kosmo-characteristic-store',
			partialize: (state) => ({
				currentCharacteristics: state.currentCharacteristics,
				currentSuggestions: state.currentSuggestions,
				chatHistories: state.chatHistories,
				selectedId: state.selectedId,
			}),
		},
	),
);

export const clearCharacteristicStore = () => {
	useCharacteristicStore.persist.clearStorage();
	useCharacteristicStore.setState({
		currentCharacteristics: [],
		currentSuggestions: [],
		chatHistories: {},
		selectedId: null,
	});
};
