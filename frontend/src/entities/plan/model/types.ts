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
	origin?: string;
	rationale?: string;
	userVersion?: string;
}
