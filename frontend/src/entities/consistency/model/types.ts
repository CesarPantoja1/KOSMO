type Phase = 'discovery' | 'features' | 'requirements' | 'modeling';

export interface ConsistencyCheck {
	project_id: string;
	phase_origin: string;
	phase_destination?: string;
	changes: {
		section: string;
		diff_before: string;
		diff_after: string;
	}[];
}

export interface ConsistencyReportResponse {
	source_type: Phase;
	source_id: string;
	target_type?: Phase;
	your_changes: YourChange[];
	downstream_impact: DownstreamProposal[];
}

export interface YourChange {
	change_id: string;
	section: string;
	description: string;
	diff: { before: string; after: string };
	accepted: boolean;
}

export interface DownstreamProposal {
	id: string;
	phase: string;
	targetId: string;
	artifact_type: string;
	targetDisplayId: string;
	targetTitle: string;
	section: string;
	rationale: string;
	action?: string;
	diff?: { field: string; before: string; after: string };
	accepted?: boolean;
}
