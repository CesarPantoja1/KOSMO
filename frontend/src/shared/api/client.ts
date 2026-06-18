import { API_BASE_URL } from './config';
import { useAuthStore } from '../store/auth.store';
import { TokenPairResponse } from './auth';

let isRefreshing = false;
let failedQueue: { resolve: (value?: unknown) => void; reject: (reason?: any) => void }[] = [];

const processQueue = (error: Error | null, token: string | null = null) => {
	failedQueue.forEach((prom) => {
		if (error) {
			prom.reject(error);
		} else {
			prom.resolve(token);
		}
	});
	failedQueue = [];
};

export const apiClient = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
	const { accessToken, refreshToken, setTokens, clearAuth, mockUserId } = useAuthStore.getState();
	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	const headers = new Headers(options.headers || {});
	
	if (isAuthDisabled) {
		if (mockUserId && !headers.has('X-Mock-User')) {
			headers.set('X-Mock-User', mockUserId);
		}
	} else if (accessToken && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${accessToken}`);
	}

	const config: RequestInit = {
		...options,
		headers,
	};

	let res = await fetch(`${API_BASE_URL}${url}`, config);

	if (!isAuthDisabled && res.status === 401 && refreshToken && !url.includes('/auth/token')) {
		if (isRefreshing) {
			return new Promise((resolve, reject) => {
				failedQueue.push({ resolve, reject });
			})
				.then((token) => {
					headers.set('Authorization', `Bearer ${token}`);
					return fetch(`${API_BASE_URL}${url}`, { ...config, headers });
				})
				.then(async (retryRes) => {
					if (!retryRes.ok) throw new Error('API Error');
					return retryRes.json();
				});
		}

		isRefreshing = true;

		try {
			const refreshRes = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ grant_type: 'refresh_token', refresh_token: refreshToken }),
			});

			if (!refreshRes.ok) {
				throw new Error('Refresh failed');
			}

			const tokens: TokenPairResponse = await refreshRes.json();
			setTokens(tokens.access.token, tokens.refresh.token);

			headers.set('Authorization', `Bearer ${tokens.access.token}`);
			processQueue(null, tokens.access.token);

			res = await fetch(`${API_BASE_URL}${url}`, { ...config, headers });
		} catch (err) {
			processQueue(err as Error, null);
			clearAuth();
			// Redirigir a login si expira
			// if (typeof window !== 'undefined') {
			// 	window.location.href = '/login';
			// }
			throw err;
		} finally {
			isRefreshing = false;
		}
	}

	if (!res.ok) {
		let message = 'API Error';
		try {
			const data = await res.json();
			if (data.detail) message = data.detail;
		} catch (e) {}
		const error = new Error(message) as Error & { status?: number };
		error.status = res.status;
		throw error;
	}
	
	// handle 204 No Content
	if (res.status === 204) return null as T;

	return res.json();
};
