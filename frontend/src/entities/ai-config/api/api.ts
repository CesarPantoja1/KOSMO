import { apiClient } from '@/shared/api/client';
import type {
	AIConfigView,
	AIProviderInfo,
	SaveAIConfigRequest,
	TestAIConnectionRequest,
	TestAIConnectionResult,
} from '../model/types';

export const aiConfigApi = {
	async getProviders(): Promise<AIProviderInfo[]> {
		return apiClient<AIProviderInfo[]>('/api/v1/ai-config/providers', { method: 'GET' });
	},

	async getConfig(): Promise<AIConfigView> {
		return apiClient<AIConfigView>('/api/v1/ai-config', { method: 'GET' });
	},

	async saveConfig(data: SaveAIConfigRequest): Promise<AIConfigView> {
		return apiClient<AIConfigView>('/api/v1/ai-config', {
			method: 'POST',
			body: JSON.stringify(data),
		});
	},

	async deleteConfig(): Promise<void> {
		return apiClient<void>('/api/v1/ai-config', { method: 'DELETE' });
	},

	async testConnection(data: TestAIConnectionRequest): Promise<TestAIConnectionResult> {
		return apiClient<TestAIConnectionResult>('/api/v1/ai-config/test', {
			method: 'POST',
			body: JSON.stringify(data),
		});
	},
};
