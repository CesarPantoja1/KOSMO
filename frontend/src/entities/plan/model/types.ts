export type PlanChangeStatus = 'pending' | 'accepted' | 'conflict' | 'discarded';

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
	phase: string;
	context: string;
	changes: PlanChange[];
	pending_count: number;
	conflict_count: number;
}

export interface CollisionItem {
	id: string;
	section: string;
	diff_before: string;
	diff_after: string;
	status: PlanChangeStatus;
	origin: string;
	phase: string;
	context: string;
	rationale: string;
	created_at: string;
}

export interface CollisionResponse {
	has_collision: boolean;
	collisions: CollisionItem[];
}

export interface AppliedItem {
	change_id: string;
	section: string;
}

export interface FailedItem {
	change_id: string;
	section: string;
	error: string;
}

export interface AffectedPhase {
	phase: string;
	affected_count: number;
	affected_ids: string[];
}

export interface ApplyResponse {
	applied: AppliedItem[];
	failed: FailedItem[];
	propagation: {
		affected_phases: AffectedPhase[];
	};
}
