export type DeployStatus = 'idle' | 'pending' | 'building' | 'ready' | 'failed';

export type PreconditionState =
	| 'loading'
	| 'github-not-linked'
	| 'github-not-synced'
	| 'railway-not-linked'
	| 'ready';

export interface ProjectDeployStatusResponse {
	service_id: string | null;
	service_name: string | null;
	deploy_url: string | null;
	status: DeployStatus;
	last_deploy_at: string | null;
	error_message: string | null;
	error_log_url: string | null;
}

export interface DeployRailwayRequest {
	service_name?: string | null;
	environment_variables?: Record<string, string> | null;
}
