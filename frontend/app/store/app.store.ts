import { usePlanStore } from '@/entities/plan';
import { useDiscoveryStore } from '@/entities/discovery';
import { useCharacteristicStore } from '@/entities/characteristic';
import { useModelingStore } from '@/entities/modeling';
import { useRequirementsStore } from '@/entities/requirements';
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
			},
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),
			hasUnsavedChanges: false,
			setHasUnsavedChanges: (v) => set({ hasUnsavedChanges: v }),
			pendingNavigationPath: null,
			setPendingNavigationPath: (v) => set({ pendingNavigationPath: v }),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),
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
