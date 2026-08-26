export { apiClient } from './client';
export { ApiError, formatApiError, parseApiError } from './errors';
export type { ApiViolation } from './errors';
export { authHeaders } from './headers';
export { authApi } from './auth';
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
} from './auth.types';
