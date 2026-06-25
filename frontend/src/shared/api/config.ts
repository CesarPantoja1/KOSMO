const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

if (process.env.NODE_ENV === 'production' && (!apiBaseUrl || apiBaseUrl.includes('localhost'))) {
	throw new Error('NEXT_PUBLIC_API_URL must point to the production backend URL');
}

export const API_BASE_URL = apiBaseUrl ?? 'http://localhost:8000';
