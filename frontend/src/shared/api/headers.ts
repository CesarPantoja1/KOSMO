import { useAuthStore } from '../store/auth.store';

export function authHeaders(extra: HeadersInit = {}): Headers {
	const headers = new Headers(extra);
	const { accessToken, mockUserId } = useAuthStore.getState();
	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	if (isAuthDisabled) {
		if (mockUserId && !headers.has('X-Mock-User')) {
			headers.set('X-Mock-User', mockUserId);
		}
	} else if (accessToken && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${accessToken}`);
	}

	return headers;
}
