import { apiClient } from '@/shared/api';
import type { DiscoveryResponse } from '../types/discovery';

export const getDiscovery = (projectId: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'GET',
	});
};

export const saveDiscovery = (projectId: string, content: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({ content }),
	});
};

export const generateDiscovery = (projectId: string) => {
	return apiClient<DiscoveryResponse>(`/api/v1/projects/${projectId}/discovery`, {
		method: 'POST',
	});
};
