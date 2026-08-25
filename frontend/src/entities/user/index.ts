// TYPES
export type {
	RegisterRequest,
	AuthorizeRequest,
	TokenExchangeRequest,
	TokenRefreshRequest,
	LogoutRequest,
	UserPublic,
	AuthorizationCodeResponse,
	TokenView,
	TokenPairResponse,
	PrincipalView,
	OAuthErrorResponse,
	User,
} from './model/types';

export type {
	AIProvider,
	AIConfigView,
	SaveAIConfigRequest,
	TestAIConnectionRequest,
	TestAIConnectionResult,
} from './model/ai-config';

export {
	AI_PROVIDERS,
	DEFAULT_AI_PROVIDER,
	DEFAULT_AI_MODEL,
	getProviderLabel,
	getProviderModels,
	maskApiKey,
} from './model/ai-config';

// SCHEMA
export { UserSchema } from './model/user-schema';

// STORE
export { useAuthStore, clearAuthStore } from './model/store';
export type { AuthState } from './model/store';

export { useAiConfigStore } from './model/ai-config-store';
export type { AiConfigState } from './model/ai-config-store';

// API
export { authApi } from './api/auth';
export { authHeaders } from './api/headers';
export { getUser } from './api/user-api';
export { aiConfigApi } from './api/ai-config-api';

// UI
export { UserCard } from './ui/UserCard';
export { AiConfigForm } from './ui/AiConfigForm';
export { AiProviderBadge } from './ui/AiProviderBadge';
