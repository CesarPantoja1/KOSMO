import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from './types';
import { getProjects, getProject } from '../api/api';

interface ProjectStore {
	currentProject: Project | null;
	setCurrentProject: (project: Project) => void;
	clearCurrentProject: () => void;
	getProjects: () => Promise<Project[]>;
	getProject: (id: string) => Promise<Project>;
}

export const useProjectStore = create<ProjectStore>()(
	persist(
		(set) => ({
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			clearCurrentProject: () => set({ currentProject: null }),

			getProjects: async () => {
				return getProjects();
			},

			getProject: async (id) => {
				const data = await getProject(id);
				set({ currentProject: data });
				return data;
			},
		}),
		{
			name: 'kosmo-project-store',
			partialize: (state) => ({ currentProject: state.currentProject }),
		},
	),
);
