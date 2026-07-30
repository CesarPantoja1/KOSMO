export type PlanChangeStatus = 'pending' | 'added' | 'accepted' | 'applied' | 'conflict' | 'discarded';

export interface PlanChangeDiff {
	before: string;
	after: string;
}

export interface PlanChange {
	id: string;
	section: string;
	description: string;
	diff: PlanChangeDiff;
	status: PlanChangeStatus;
	origin: string;
	phase: string;
	context: string;
	rationale?: string;
	userVersion?: string;
	created_at: string;
}

export interface PlanResponse {
	project_id: string;
	phase: string;
	context: string;
	changes: PlanChange[];
	pending_count: number;
	conflict_count: number;
}

export interface FailedChange {
	id: string;
	reason: string;
}

export interface AffectedPhase {
	phase: string;
	affected_count: number;
	affected_ids: string[];
}

export interface ApplyResponse {
	applied_count: number;
	failed_count: number;
	failed_changes: FailedChange[];
	propagation: {
		affected_phases: AffectedPhase[];
	} | null;
}
