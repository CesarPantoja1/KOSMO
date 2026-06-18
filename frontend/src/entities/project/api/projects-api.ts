import { apiClient } from '@/shared/api';
import { Project } from '@/shared/types/project';

export const projectsApi = {
	getProjects: async (): Promise<Project[]> => {
		return apiClient<Project[]>('/api/v1/projects', {
			method: 'GET',
		});
	},

	getProject: async (id: string): Promise<Project> => {
		return apiClient<Project>(`/api/v1/projects/${id}`, {
			method: 'GET',
		});
	},
};
