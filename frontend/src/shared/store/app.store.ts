import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from '@/shared/types/project';

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
}

export const useAppStore = create<AppState>()(
	persist(
		(set) => ({
			initialized: false,
			setInitialized: (v) => set({ initialized: v }),
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			clearCurrentProject: () => set({ currentProject: null, isProyectosOpen: false }),
			setProjectState: (project) => set({ currentProject: project, isProyectosOpen: true }),
			resetProjectState: () => set({ currentProject: null, isProyectosOpen: false }),
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),
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
