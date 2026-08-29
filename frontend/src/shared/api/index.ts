export { authApi } from './auth';
export type {
	AuthorizationCodeResponse,
	AuthorizeRequest,
	LogoutRequest,
	OAuthErrorResponse,
	PrincipalView,
	RegisterRequest,
	TokenExchangeRequest,
	TokenPairResponse,
	TokenRefreshRequest,
	TokenView,
	UserPublic,
} from './auth.types';
export { apiClient } from './client';
export { ApiError, formatApiError, parseApiError } from './errors';
export type { ApiViolation } from './errors';
export { authHeaders } from './headers';

export {
	API_BASE_URL,
	PUBLIC_APP_DOMAIN,
	USE_MOCKS,
	GITHUB_CLIENT_ID,
	GITHUB_SCOPES,
	RAILWAY_CLIENT_ID,
	RAILWAY_SCOPES,
} from './config';
