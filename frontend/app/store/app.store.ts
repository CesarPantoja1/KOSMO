import { clearConsistencyStore } from '@/entities/consistency';
import { clearPlanStore, usePlanStore } from '@/entities/plan';
import { clearDiscoveryStore, useDiscoveryStore } from '@/entities/discovery';
import { getDiscovery } from '@/entities/discovery/api/api';
import { clearCharacteristicStore, useCharacteristicStore } from '@/entities/characteristic';
import { getCharacteristics } from '@/entities/characteristic/api/api';
import { clearModelingStore, useModelingStore } from '@/entities/modeling';
import { getDiagram } from '@/entities/modeling/api/api';
import { clearRequirementsStore, useRequirementsStore } from '@/entities/requirements';
import { getRequirements } from '@/entities/requirements/api/api';
import { clearProjectStore } from '@/entities/project';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
	initialized: boolean;
	setInitialized: (v: boolean) => void;
	resetProjectState: () => void;
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
			resetProjectState: () => {
				clearProjectStore();
				clearDiscoveryStore();
				clearPlanStore();
				clearCharacteristicStore();
				clearModelingStore();
				clearRequirementsStore();
				clearConsistencyStore();
				set({
					initialized: false,
					hasUnsavedChanges: false,
					pendingNavigationPath: null,
					isEditorMaximized: false,
				});
			},
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
								const content = reqResult.value?.document_markdown ?? '';
								useRequirementsStore.getState().setHasRequirements(c.id, !!content);
								if (content) {
									useRequirementsStore.getState().setCurrentRequirements(c.id, content);
								}
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
			partialize: () => ({}),
		},
	),
);

export const clearAppStore = () => {
	useAppStore.persist.clearStorage();
	useAppStore.setState({
		initialized: false,
		hasUnsavedChanges: false,
		pendingNavigationPath: null,
		isEditorMaximized: false,
	});
};
