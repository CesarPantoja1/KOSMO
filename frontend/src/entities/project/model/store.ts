import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from './types';
import { getProjects, getProject } from '../api/api';

interface ProjectStore {
	projects: Project[];
	setProjects: (projects: Project[]) => void;
	addProject: (project: Project) => void;
	currentProject: Project | null;
	setCurrentProject: (project: Project) => void;
	setProjectState: (project: Project) => void;
	isProyectosOpen: boolean;
	setIsProyectosOpen: (v: boolean) => void;
	getProjects: () => Promise<Project[]>;
	getProject: (id: string) => Promise<Project>;
}

export const useProjectStore = create<ProjectStore>()(
	persist(
		(set) => ({
			projects: [],
			setProjects: (projects) => set({ projects }),
			addProject: (project) =>
				set((state) => ({ projects: [...state.projects, project] })),
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			setProjectState: (project) =>
				set({ currentProject: project, isProyectosOpen: true }),
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),

			getProjects: async () => {
				const data = await getProjects();
				set({ projects: data });
				return data;
			},

			getProject: async (id) => {
				const data = await getProject(id);
				set({ currentProject: data });
				return data;
			},
		}),
		{
			name: 'kosmo-project-store',
			partialize: (state) => ({
				currentProject: state.currentProject,
				isProyectosOpen: state.isProyectosOpen,
			}),
		},
	),
);

export const clearProjectStore = () => {
	useProjectStore.persist.clearStorage();
	useProjectStore.setState({
		projects: [],
		currentProject: null,
		isProyectosOpen: false,
	});
};

export const clearProjectStoreExceptProjects = () => {
	useProjectStore.setState({ currentProject: null, isProyectosOpen: false });
};
