import { apiClient } from '@/shared/api';
import type { Project } from '@/entities/project/model/types';

interface CreateProjectBody {
	name: string;
	description: string;
}

export const createProject = (body: CreateProjectBody) => {
	const token = localStorage.getItem('token') || '';

	return apiClient<Project>('/api/v1/projects', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(body),
	});
};
