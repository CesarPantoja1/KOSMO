import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { USE_MOCKS } from '@/shared/api/config';

interface ModelingStore {
	hasDiagram: Record<string, boolean>;
	setHasDiagram: (id: string, has: boolean) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;
}

export const isUsingMocks = () => USE_MOCKS;

export const useModelingStore = create<ModelingStore>()(
	persist(
		(set) => ({
			hasDiagram: {},
			setHasDiagram: (id, has) =>
				set((state) => ({
					hasDiagram: { ...state.hasDiagram, [id]: has },
				})),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),
		}),
		{
			name: 'kosmo-modeling-store',
			partialize: (state) => ({ hasDiagram: state.hasDiagram }),
		},
	),
);
