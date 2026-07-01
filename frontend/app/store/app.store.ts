import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from '@/entities/project/model/types';

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
	hasRequirements: Record<string, boolean>;
	setHasRequirements: (id: string, has: boolean) => void;
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
			resetProjectState: () =>
				set({
					currentProject: null,
					isProyectosOpen: false,
					hasUnsavedChanges: false,
					pendingNavigationPath: null,
				}),
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),
			hasUnsavedChanges: false,
			setHasUnsavedChanges: (v) => set({ hasUnsavedChanges: v }),
			pendingNavigationPath: null,
			setPendingNavigationPath: (v) => set({ pendingNavigationPath: v }),
			hasRequirements: {},
			setHasRequirements: (id, has) => set((state) => ({ hasRequirements: { ...state.hasRequirements, [id]: has } })),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),
		}),
		{
			name: 'kosmo-app-store',
			partialize: (state) => ({
				currentProject: state.currentProject,
				isProyectosOpen: state.isProyectosOpen,
				hasRequirements: state.hasRequirements,
			}),
		},
	),
);
