import { useOAuthIntegration } from './useOAuthIntegration';
import { buildGitHubAuthUrl, buildRailwayAuthUrl, DEFAULT_REDIRECT_URI } from './oauth-config';
import type { IntegrationStatus } from './types';

interface OAuthHookOptions {
	redirectUri?: string;
	onStatusChange?: (status: IntegrationStatus) => void;
}

export function useGithubOAuth({ redirectUri = DEFAULT_REDIRECT_URI, onStatusChange }: OAuthHookOptions = {}) {
	return useOAuthIntegration({
		provider: 'github',
		label: 'GitHub',
		messageType: 'github-oauth-code',
		redirectUri,
		buildAuthUrl: buildGitHubAuthUrl,
		onStatusChange,
	});
}

export function useRailwayOAuth({ redirectUri = DEFAULT_REDIRECT_URI, onStatusChange }: OAuthHookOptions = {}) {
	return useOAuthIntegration({
		provider: 'railway',
		label: 'Railway',
		messageType: 'railway-oauth-code',
		redirectUri,
		buildAuthUrl: buildRailwayAuthUrl,
		onStatusChange,
	});
}
