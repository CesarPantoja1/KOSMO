export type IntegrationProvider = 'github' | 'railway';

export interface IntegrationStatus {
	provider: IntegrationProvider;
	is_connected: boolean;
	username?: string | null;
	connected_at?: string | null;
}

export interface ConnectOAuthRequest {
	code: string;
	redirect_uri?: string | null;
	code_verifier?: string | null;
}
