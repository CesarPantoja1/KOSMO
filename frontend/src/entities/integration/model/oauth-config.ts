import { PUBLIC_APP_DOMAIN } from '@/shared/api';

type OAuthProvider = 'github' | 'railway';

export interface OAuthAuthorizationRequest {
	state: string;
	codeChallenge: string;
}

interface RuntimeConfig {
	githubClientId?: string;
	githubScopes?: string;
	railwayClientId?: string;
	railwayScopes?: string;
	publicAppDomain?: string;
}

declare global {
	interface Window {
		__KOSMO_RUNTIME_CONFIG__?: RuntimeConfig;
	}
}

const GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize';
const RAILWAY_AUTH_URL = 'https://backboard.railway.com/oauth/auth';

function runtimeConfig(): RuntimeConfig {
	if (typeof window === 'undefined') return {};
	return window.__KOSMO_RUNTIME_CONFIG__ ?? {};
}

function randomState(): string {
	const bytes = new Uint8Array(24);
	globalThis.crypto.getRandomValues(bytes);
	return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

const stateKey = (provider: OAuthProvider) => `kosmo.oauth.${provider}.state`;
const verifierKey = (provider: OAuthProvider) => `kosmo.oauth.${provider}.verifier`;

function base64Url(bytes: Uint8Array): string {
	let binary = '';
	for (const byte of bytes) binary += String.fromCharCode(byte);
	return globalThis.btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

export function createOAuthState(provider: OAuthProvider): string {
	const state = `${provider}.${randomState()}`;
	window.sessionStorage.setItem(stateKey(provider), state);
	return state;
}

export async function createOAuthAuthorization(
	provider: OAuthProvider,
): Promise<OAuthAuthorizationRequest> {
	const state = createOAuthState(provider);
	const verifier = base64Url(globalThis.crypto.getRandomValues(new Uint8Array(48)));
	window.sessionStorage.setItem(verifierKey(provider), verifier);
	const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
	return { state, codeChallenge: base64Url(new Uint8Array(digest)) };
}

export function consumeOAuthState(provider: OAuthProvider, returnedState: unknown): boolean {
	if (typeof returnedState !== 'string' || !returnedState) return false;
	const expected = window.sessionStorage.getItem(stateKey(provider));
	window.sessionStorage.removeItem(stateKey(provider));
	return expected !== null && expected === returnedState;
}

export function consumeOAuthCodeVerifier(provider: OAuthProvider): string | null {
	const verifier = window.sessionStorage.getItem(verifierKey(provider));
	window.sessionStorage.removeItem(verifierKey(provider));
	return verifier;
}

export function getDefaultRedirectUri(): string {
	const domain = runtimeConfig().publicAppDomain || PUBLIC_APP_DOMAIN;
	return `${domain.replace(/\/$/, '')}/perfil`;
}

// Compatibilidad para consumidores que solo necesitan el valor durante SSR o tests.
export const DEFAULT_REDIRECT_URI = `${PUBLIC_APP_DOMAIN}/perfil`;

function githubClientId(): string {
	return runtimeConfig().githubClientId || process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || '';
}

function githubScopes(): string {
	return runtimeConfig().githubScopes || process.env.NEXT_PUBLIC_GITHUB_SCOPES || 'repo';
}

function railwayClientId(): string {
	return runtimeConfig().railwayClientId || process.env.NEXT_PUBLIC_RAILWAY_CLIENT_ID || '';
}

function railwayScopes(): string {
	return (
		runtimeConfig().railwayScopes ||
		process.env.NEXT_PUBLIC_RAILWAY_SCOPES ||
		'openid email profile offline_access workspace:admin'
	);
}

export function buildGitHubAuthUrl(redirectUri: string, state: string, codeChallenge: string): string {
	const url = new URL(GITHUB_AUTH_URL);
	url.searchParams.set('client_id', githubClientId());
	url.searchParams.set('scope', githubScopes());
	url.searchParams.set('redirect_uri', redirectUri);
	url.searchParams.set('state', state);
	url.searchParams.set('code_challenge', codeChallenge);
	url.searchParams.set('code_challenge_method', 'S256');
	return url.toString();
}

export function buildRailwayAuthUrl(redirectUri: string, state: string, codeChallenge: string): string {
	const url = new URL(RAILWAY_AUTH_URL);
	url.searchParams.set('response_type', 'code');
	url.searchParams.set('client_id', railwayClientId());
	url.searchParams.set('scope', railwayScopes());
	url.searchParams.set('redirect_uri', redirectUri);
	url.searchParams.set('state', state);
	url.searchParams.set('code_challenge', codeChallenge);
	url.searchParams.set('code_challenge_method', 'S256');
	url.searchParams.set('prompt', 'consent');
	return url.toString();
}
