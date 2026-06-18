import { apiClient } from '@/shared/api';
import type { DiscoveryResponse } from '../types/discovery';

export const getDiscovery = (projectId: string) => {
	const token = localStorage.getItem('token') || '';

	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'GET',
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});
};
