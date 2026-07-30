import { create } from 'zustand';
import type { SuggestCharacteristic, CharacteristicResponse } from './types';
import {
	getCharacteristics,
	generateCharacteristics,
	getSuggestCharacteristics,
	addCharacteristic,
} from '../api/api';

interface CharacteristicStore {
	currentCharacteristics: CharacteristicResponse[];
	setCurrentCharacteristics: (characteristics: CharacteristicResponse[]) => void;
	currentSuggestions: SuggestCharacteristic[];
	setCurrentSuggestions: (suggestions: SuggestCharacteristic[]) => void;
	clearCharacteristics: () => void;
	getCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	generateCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	getSuggestCharacteristics: (projectId: string) => Promise<SuggestCharacteristic[]>;
	addCharacteristic: (
		projectId: string,
		item: { title: string; description: string },
	) => Promise<CharacteristicResponse>;
}

export const useCharacteristicStore = create<CharacteristicStore>()((set) => ({
	currentCharacteristics: [],
	setCurrentCharacteristics: (characteristics) =>
		set({ currentCharacteristics: characteristics }),
	currentSuggestions: [],
	setCurrentSuggestions: (suggestions) => set({ currentSuggestions: suggestions }),
	clearCharacteristics: () =>
		set({ currentCharacteristics: [], currentSuggestions: [] }),

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
		set((state) => ({
			currentCharacteristics: [...state.currentCharacteristics, data],
		}));
		return data;
	},
}));
