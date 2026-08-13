import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
	getDiagram as getDiagramApi,
	generatePlantUmlDiagram as generatePlantUmlDiagramApi,
} from '../api/api';

interface ModelingStore {
	currentDiagrams: Record<string, string>;
	setCurrentDiagrams: (featureId: string, content: string) => void;
	getDiagram: (projectId: string, featureId: string) => Promise<string>;
	generatePlantUmlDiagram: (
		projectId: string,
		featureId: string,
	) => Promise<string>;

	hasDiagram: Record<string, boolean>;
	setHasDiagram: (id: string, has: boolean) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;
	resetModeling: () => void;
}

export const useModelingStore = create<ModelingStore>()(
	persist(
		(set, _get) => ({
			currentDiagrams: {},
			setCurrentDiagrams: (featureId, content) =>
				set((state) => ({
					currentDiagrams: { ...state.currentDiagrams, [featureId]: content },
				})),
			getDiagram: async (projectId, featureId) => {
				const data = await getDiagramApi(projectId, featureId);
				const content = data.diagram_syntax;
				if (content) {
					set((state) => ({
						currentDiagrams: { ...state.currentDiagrams, [featureId]: content },
						hasDiagram: { ...state.hasDiagram, [featureId]: true },
					}));
				}
				return content;
			},
			generatePlantUmlDiagram: async (projectId, featureId) => {
				const data = await generatePlantUmlDiagramApi(projectId, featureId);
				const content = data.diagram_syntax;
				set((state) => ({
					currentDiagrams: { ...state.currentDiagrams, [featureId]: content },
					hasDiagram: { ...state.hasDiagram, [featureId]: true },
				}));
				return content;
			},

			hasDiagram: {},
			setHasDiagram: (id, has) =>
				set((state) => ({
					hasDiagram: { ...state.hasDiagram, [id]: has },
				})),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),
			resetModeling: () => set({ hasDiagram: {}, currentDiagrams: {}, isEditorMaximized: false }),
		}),
		{
			name: 'kosmo-modeling-store',
			partialize: (state) => ({
				hasDiagram: state.hasDiagram,
				currentDiagrams: state.currentDiagrams,
			}),
		},
	),
);

export const clearModelingStore = () => {
	useModelingStore.persist.clearStorage();
	useModelingStore.setState({ hasDiagram: {}, currentDiagrams: {}, isEditorMaximized: false });
};
