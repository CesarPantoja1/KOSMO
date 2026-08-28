const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

// The production frontend is served by the same Nginx origin as the API.
// Leaving this unset therefore keeps the image portable between staging and
// production: requests such as `/api/v1/projects` stay on the current host.
export const API_BASE_URL =
	apiBaseUrl || (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000');

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === 'true';
export const PUBLIC_APP_DOMAIN = process.env.NEXT_DOMAIN_APP || 'http://localhost:3000';

// GITHUB
export const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || '';
export const GITHUB_SCOPES = 'repo';
