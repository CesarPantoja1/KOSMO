import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ModelingStore {
	hasDiagram: Record<string, boolean>;
	setHasDiagram: (id: string, has: boolean) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;
	resetModeling: () => void;
}

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
			resetModeling: () => set({ hasDiagram: {}, isEditorMaximized: false }),
		}),
		{
			name: 'kosmo-modeling-store',
			partialize: (state) => ({ hasDiagram: state.hasDiagram }),
		},
	),
);
