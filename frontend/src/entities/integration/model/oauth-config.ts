import { PUBLIC_APP_DOMAIN } from '@/shared/api';

// GITHUB
const GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize';
export const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || '';
export const GITHUB_SCOPES =
	process.env.NEXT_PUBLIC_GITHUB_SCOPES || 'repo delete_repo';

// RAILWAY
const RAILWAY_AUTH_URL = 'https://backboard.railway.com/oauth/auth';
export const RAILWAY_CLIENT_ID = process.env.NEXT_PUBLIC_RAILWAY_CLIENT_ID || '';
export const RAILWAY_SCOPES =
	process.env.NEXT_PUBLIC_RAILWAY_SCOPES ||
	'openid email profile offline_access workspace:admin';

export function buildGitHubAuthUrl(redirectUri: string): string {
	return `${GITHUB_AUTH_URL}?client_id=${GITHUB_CLIENT_ID}&scope=${GITHUB_SCOPES}&redirect_uri=${encodeURIComponent(redirectUri)}&state=github`;
}

export function buildRailwayAuthUrl(redirectUri: string): string {
	return `${RAILWAY_AUTH_URL}?response_type=code&client_id=${RAILWAY_CLIENT_ID}&scope=${encodeURIComponent(RAILWAY_SCOPES)}&redirect_uri=${encodeURIComponent(redirectUri)}&state=railway&prompt=consent`;
}

export const DEFAULT_REDIRECT_URI = `${PUBLIC_APP_DOMAIN}/perfil`;
