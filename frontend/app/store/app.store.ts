import { useConsistencyStore } from '@/entities/consistency';
import { usePlanStore } from '@/entities/plan';
import { useDiscoveryStore } from '@/entities/discovery';
import { getDiscovery } from '@/entities/discovery/api/api';
import { useCharacteristicStore } from '@/entities/characteristic';
import { getCharacteristics } from '@/entities/characteristic/api/api';
import { useModelingStore } from '@/entities/modeling';
import { getDiagram } from '@/entities/modeling/api/api';
import { useRequirementsStore } from '@/entities/requirements';
import { getRequirements } from '@/entities/requirements/api/api';
import type { Project } from '@/entities/project/model/types';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
	initialized: boolean;
	setInitialized: (v: boolean) => void;
	currentProject: Project | null;
	setCurrentProject: (project: Project) => void;
	clearCurrentProject: () => void;
	setProjectState: (project: Project) => void;
	resetProjectState: () => void;
	isProyectosOpen: boolean;
	setIsProyectosOpen: (v: boolean) => void;
	hasUnsavedChanges: boolean;
	setHasUnsavedChanges: (v: boolean) => void;
	pendingNavigationPath: string | null;
	setPendingNavigationPath: (v: string | null) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;
	initializeProject: (projectId: string) => Promise<void>;
}

export const useAppStore = create<AppState>()(
	persist(
		(set) => ({
			initialized: false,
			setInitialized: (v) => set({ initialized: v }),
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			clearCurrentProject: () => set({ currentProject: null, isProyectosOpen: false }),
			setProjectState: (project) =>
				set({ currentProject: project, isProyectosOpen: true }),
			resetProjectState: () => {
				set({
					currentProject: null,
					isProyectosOpen: false,
					hasUnsavedChanges: false,
					pendingNavigationPath: null,
				});
				usePlanStore.getState().resetPlan();
				useDiscoveryStore.getState().resetDiscovery();
				useCharacteristicStore.getState().clearCharacteristics();
				useCharacteristicStore.getState().clearAllChatHistories();
				useModelingStore.getState().resetModeling();
				useRequirementsStore.getState().resetRequirements();
				useConsistencyStore.getState().resetConsistency();
			},
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),
			hasUnsavedChanges: false,
			setHasUnsavedChanges: (v) => set({ hasUnsavedChanges: v }),
			pendingNavigationPath: null,
			setPendingNavigationPath: (v) => set({ pendingNavigationPath: v }),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),
			initializeProject: async (projectId) => {
				try {
					const discovery = await getDiscovery(projectId);
					if (!discovery) return;
					useDiscoveryStore.getState().setCurrentDiscovery(discovery);

					await usePlanStore.getState().fetchAndHydratePlan(projectId, 'discovery');

					const characteristics = await getCharacteristics(projectId);
					if (!characteristics || characteristics.length === 0) return;
					useCharacteristicStore.getState().setCurrentCharacteristics(characteristics);

					await usePlanStore.getState().fetchAndHydratePlan(projectId, 'features');

					await Promise.allSettled(
						characteristics.map(async (c) => {
							const [reqResult, diagramResult] = await Promise.allSettled([
								getRequirements(projectId, c.id),
								getDiagram(projectId, c.id),
							]);

							if (reqResult.status === 'fulfilled') {
								useRequirementsStore.getState().setHasRequirements(c.id, !!reqResult.value);
							}
							if (diagramResult.status === 'fulfilled') {
								useModelingStore.getState().setHasDiagram(c.id, !!diagramResult.value);
							}
						}),
					);

					await usePlanStore.getState().fetchAndHydratePlan(projectId, 'requirements');
				} catch (error) {
					console.error('[initializeProject] Error:', error);
				}
			},
		}),
		{
			name: 'kosmo-app-store',
			partialize: (state) => ({
				currentProject: state.currentProject,
				isProyectosOpen: state.isProyectosOpen,
			}),
		},
	),
);
