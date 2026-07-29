export type PlanChangeStatus = 'pending' | 'accepted' | 'conflict' | 'discarded';

export interface PlanChange {
	id: string;
	section: string;
	description: string;
	diff_before: string;
	diff_after: string;
	status: PlanChangeStatus;
	origin: string;
	phase: string;
	context: string;
	rationale: string;
	created_at: string;
}

export interface PlanResponse {
	phase: string;
	context: string;
	changes: PlanChange[];
	pending_count: number;
	conflict_count: number;
}
