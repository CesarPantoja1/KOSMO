const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
const fallbackApiBaseUrl =
	process.env.NODE_ENV === 'production'
		? 'https://kosmo-backend.onrender.com'
		: 'http://localhost:8000';

export const API_BASE_URL = apiBaseUrl?.trim() || fallbackApiBaseUrl;
