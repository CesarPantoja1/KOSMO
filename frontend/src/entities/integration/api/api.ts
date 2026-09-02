import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { IntegrationProvider, IntegrationStatus, ConnectOAuthRequest } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock data ---

const mockStatuses: Record<string, IntegrationStatus> = {
	github: {
		provider: 'github',
		is_connected: true,
		username: 'mock-user',
		connected_at: new Date().toISOString(),
	},
	railway: {
		provider: 'railway',
		is_connected: true,
		username: 'mock-railway-user',
		connected_at: new Date().toISOString(),
	},
};

// --- Mock implementations ---

const mockGetStatus = async (provider: IntegrationProvider): Promise<IntegrationStatus> => {
	await delay(400);
	return { ...mockStatuses[provider] };
};

const mockConnect = async (
	provider: IntegrationProvider,
	_body: ConnectOAuthRequest,
): Promise<IntegrationStatus> => {
	await delay(800);
	mockStatuses[provider] = {
		provider,
		is_connected: true,
		username: 'mock-user',
		connected_at: new Date().toISOString(),
	};
	return { ...mockStatuses[provider] };
};

const mockDisconnect = async (provider: IntegrationProvider): Promise<void> => {
	await delay(600);
	mockStatuses[provider] = {
		provider,
		is_connected: false,
	};
};

// --- Real implementations ---

const realGetStatus = (provider: IntegrationProvider): Promise<IntegrationStatus> =>
	apiClient<IntegrationStatus>(`/api/v1/integrations/${provider}/status`, { method: 'GET' });

const realConnect = (
	provider: IntegrationProvider,
	body: ConnectOAuthRequest,
): Promise<IntegrationStatus> =>
	apiClient<IntegrationStatus>(`/api/v1/integrations/${provider}/connect`, {
		method: 'POST',
		body: JSON.stringify(body),
	});

const realDisconnect = (provider: IntegrationProvider): Promise<void> =>
	apiClient<void>(`/api/v1/integrations/${provider}`, { method: 'DELETE' });

// --- Exports (switch based on USE_MOCKS) ---

export const getIntegrationStatus = (provider: IntegrationProvider): Promise<IntegrationStatus> =>
	USE_MOCKS ? mockGetStatus(provider) : realGetStatus(provider);

export const connectIntegration = (
	provider: IntegrationProvider,
	body: ConnectOAuthRequest,
): Promise<IntegrationStatus> =>
	USE_MOCKS ? mockConnect(provider, body) : realConnect(provider, body);

export const disconnectIntegration = (provider: IntegrationProvider): Promise<void> =>
	USE_MOCKS ? mockDisconnect(provider) : realDisconnect(provider);
