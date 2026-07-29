import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { USE_MOCKS } from '@/shared/api/config';
import type { Project } from './types';

interface ProjectStore {
	currentProject: Project | null;
	setCurrentProject: (project: Project) => void;
	clearCurrentProject: () => void;
}

export const isUsingMocks = () => USE_MOCKS;

export const useProjectStore = create<ProjectStore>()(
	persist(
		(set) => ({
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			clearCurrentProject: () => set({ currentProject: null }),
		}),
		{
			name: 'kosmo-project-store',
			partialize: (state) => ({ currentProject: state.currentProject }),
		},
	),
);
