export interface Project {
	id: string;
	name: string;
	slug: string;
	description: string;
	owner_id: string;
	created_at: string;
	updated_at: string;
	current_phase?: string;
	status?: string;
}

export type GitHubSyncStatus = 'not_created' | 'created' | 'syncing' | 'synced' | 'failed';

export interface ProjectGitHubStatus {
	has_repository: boolean;
	repo_name?: string | null;
	repo_url?: string | null;
	is_public?: boolean | null;
	last_push_at?: string | null;
	last_commit_hash?: string | null;
	sync_status: GitHubSyncStatus;
	suggested_repo_name?: string | null;
	error_message?: string | null;
}

export interface PushGitHubRequest {
	repo_name?: string | null;
	is_public?: boolean | null;
	commit_message?: string | null;
}
