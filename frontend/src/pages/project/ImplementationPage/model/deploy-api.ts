import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { ProjectDeployStatusResponse, DeployRailwayRequest } from './deploy-types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockStatus: ProjectDeployStatusResponse = {
	service_id: null,
	service_name: null,
	deploy_url: null,
	status: 'idle',
	last_deploy_at: null,
	error_message: null,
	error_log_url: null,
};

const mockGetStatus = async (projectId: string): Promise<ProjectDeployStatusResponse> => {
	void projectId;
	await delay(400);
	return { ...mockStatus };
};

const mockStartRailway = async (
	projectId: string,
	_body?: DeployRailwayRequest,
): Promise<ProjectDeployStatusResponse> => {
	void projectId;
	await delay(1200);
	mockStatus.status = 'building';
	mockStatus.service_id = 'srv_mock_123';
	mockStatus.service_name = 'kosmo-app';
	mockStatus.last_deploy_at = new Date().toISOString();
	return { ...mockStatus };
};

const realGetStatus = (projectId: string): Promise<ProjectDeployStatusResponse> =>
	apiClient<ProjectDeployStatusResponse>(`/api/v1/projects/${projectId}/deploy`, {
		method: 'GET',
	});

const realStartRailway = (
	projectId: string,
	body?: DeployRailwayRequest,
): Promise<ProjectDeployStatusResponse> =>
	apiClient<ProjectDeployStatusResponse>(`/api/v1/projects/${projectId}/deploy/railway`, {
		method: 'POST',
		body: body ? JSON.stringify(body) : undefined,
	});

export const getDeployStatus = (projectId: string): Promise<ProjectDeployStatusResponse> =>
	USE_MOCKS ? mockGetStatus(projectId) : realGetStatus(projectId);

export const startDeployRailway = (
	projectId: string,
	body?: DeployRailwayRequest,
): Promise<ProjectDeployStatusResponse> =>
	USE_MOCKS ? mockStartRailway(projectId, body) : realStartRailway(projectId, body);
