import { useConsistencyGateStore } from '@/entities/consistency';
import { clearDiscoveryStore, useDiscoveryStore } from '@/entities/discovery';
import { getDiscovery } from '@/entities/discovery/api/api';
import {
	clearCharacteristicStore,
	useCharacteristicStore,
} from '@/entities/characteristic';
import { getCharacteristics } from '@/entities/characteristic/api/api';
import { clearModelingStore, useModelingStore } from '@/entities/modeling';
import { getDiagram } from '@/entities/modeling/api/api';
import { clearRequirementsStore, useRequirementsStore } from '@/entities/requirements';
import { getRequirements } from '@/entities/requirements/api/api';
import { clearImplementationStore } from '@/entities/implementation';
import { useChatSessionsStore } from '@/entities/chat';
import { ApiError } from '@/shared/api';
import { clearProjectStore } from '@/entities/project';
import { create } from 'zustand';
import { clearProjectStoreExceptProjects } from '@/entities/project/model/store';

interface AppState {
	initialized: boolean;
	setInitialized: (v: boolean) => void;
	resetProjectState: () => void;
	resetStateBeforeChangeProject: () => void;
	hasUnsavedChanges: boolean;
	setHasUnsavedChanges: (v: boolean) => void;
	pendingNavigationPath: string | null;
	setPendingNavigationPath: (v: string | null) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;
	initializeProject: (projectId: string) => Promise<void>;
}

export const useAppStore = create<AppState>()((set) => ({
	initialized: false,
	setInitialized: (v) => set({ initialized: v }),
	resetProjectState: () => {
				clearProjectStore();
				clearDiscoveryStore();
				clearCharacteristicStore();
				clearModelingStore();
				clearRequirementsStore();
				clearImplementationStore();
				useChatSessionsStore.getState().reset();
				useConsistencyGateStore.getState().reset();
				set({
					initialized: false,
					hasUnsavedChanges: false,
					pendingNavigationPath: null,
					isEditorMaximized: false,
				});
			},
			resetStateBeforeChangeProject: () => {
				clearProjectStoreExceptProjects();
				clearDiscoveryStore();
				clearCharacteristicStore();
				clearModelingStore();
				clearRequirementsStore();
				clearImplementationStore();
				useChatSessionsStore.getState().reset();
				useConsistencyGateStore.getState().reset();
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
					// El 404 es el caso normal cuando aún no existe el documento de descubrimiento
					try {
						const discovery = await getDiscovery(projectId);
						if (discovery) {
							useDiscoveryStore.getState().setCurrentDiscovery(discovery);
						}
					} catch (error) {
						if (!(error instanceof ApiError && error.status === 404)) {
							throw error;
						}
					}

					const characteristics = await getCharacteristics(projectId);
					if (!characteristics || characteristics.length === 0) return;
					useCharacteristicStore.getState().setCurrentCharacteristics(characteristics);

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
			} catch (error) {
				console.error('[initializeProject] Error:', error);
			}
		},
	}),
);

export const clearAppStore = () => {
	useAppStore.setState({
		initialized: false,
		hasUnsavedChanges: false,
		pendingNavigationPath: null,
		isEditorMaximized: false,
	});
};
