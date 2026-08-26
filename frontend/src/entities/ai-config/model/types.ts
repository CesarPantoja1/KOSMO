export type AIProvider = 'openai' | 'anthropic' | 'google' | 'openrouter' | 'deepseek';

export const AI_PROVIDERS: { value: AIProvider; label: string; models: string[] }[] = [
	{
		value: 'openai',
		label: 'OpenAI',
		models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1', 'o3-mini'],
	},
	{
		value: 'anthropic',
		label: 'Anthropic',
		models: [
			'claude-3-5-sonnet-20241022',
			'claude-3-5-haiku-20241022',
			'claude-3-opus-20240229',
		],
	},
	{
		value: 'google',
		label: 'Google Gemini',
		models: ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash', 'gemini-1.5-pro'],
	},
	{
		value: 'openrouter',
		label: 'OpenRouter',
		models: [
			'deepseek/deepseek-chat',
			'deepseek/deepseek-r1',
			'meta-llama/llama-3.3-70b-instruct',
			'anthropic/claude-3.5-sonnet',
			'openai/gpt-4o',
		],
	},
];

export const DEFAULT_AI_PROVIDER: AIProvider = 'google';
export const DEFAULT_AI_MODEL = 'gemini-2.5-flash';

export interface AIConfigView {
	provider: AIProvider;
	model: string;
	is_custom: boolean;
	has_api_key: boolean;
	masked_key: string | null;
	updated_at: string | null;
}

export interface SaveAIConfigRequest {
	provider: AIProvider;
	model: string;
	api_key: string;
}

export interface TestAIConnectionRequest {
	provider: AIProvider;
	model: string;
	api_key: string;
}

export interface TestAIConnectionResult {
	is_connected: boolean;
	detected_model: string;
	message: string;
}

export function getProviderLabel(provider: AIProvider): string {
	return AI_PROVIDERS.find((p) => p.value === provider)?.label ?? provider;
}

export function getProviderModels(provider: AIProvider): string[] {
	return AI_PROVIDERS.find((p) => p.value === provider)?.models ?? [];
}

export function maskApiKey(key: string | null): string | null {
	if (!key) return null;
	const stripped = key.trim();
	if (!stripped) return null;
	if (stripped.length <= 4) return '••••••••';
	return `••••••••${stripped.slice(-4)}`;
}
