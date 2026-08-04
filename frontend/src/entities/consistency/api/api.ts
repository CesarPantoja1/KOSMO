import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import { ConsistencyCheck, ConsistencyReportResponse, DownstreamProposal, YourChange } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Backend response types ---

interface BackendImpactItem {
	id: string;
	phase: string;
	targetId: string;
	artifact_type: string;
	targetDisplayId: string;
	targetTitle: string;
	section: string;
	rationale: string;
	action?: string;
	diff?: { field?: string; before?: string; after?: string } | null;
}

interface BackendYourChange {
	change_id: string;
	section: string;
	description: string;
	diff: { before: string; after: string };
	accepted: boolean;
}

interface BackendConsistencyReport {
	report_id: string;
	source_type: string;
	source_id: string;
	your_changes: BackendYourChange[];
	upstream_impact: BackendImpactItem[];
	downstream_impact: BackendImpactItem[];
}

// --- Mapping ---

function mapImpact(item: BackendImpactItem): DownstreamProposal {
	return {
		id: item.id,
		phase: item.phase,
		targetId: item.targetId,
		artifact_type: item.artifact_type,
		targetDisplayId: item.targetDisplayId,
		targetTitle: item.targetTitle,
		section: item.section,
		rationale: item.rationale,
		action: item.action || 'update',
		diff: item.diff
			? {
					field: item.diff.field ?? item.section ?? '',
					before: item.diff.before ?? '',
					after: item.diff.after ?? '',
				}
			: undefined,
		accepted: false,
	};
}

function mapChange(item: BackendYourChange): YourChange {
	return {
		change_id: item.change_id,
		section: item.section,
		description: item.description,
		diff: item.diff,
		accepted: item.accepted,
	};
}

// --- Mocks ---

const mockChecklistResponses: ConsistencyReportResponse[] = [
	{
		source_type: 'discovery',
		source_id: 'prj_01KT...',
		target_type: 'features',
		your_changes: [
			{
				change_id: 'chg_01KT...',
				section: 'Alcance del producto',
				description: 'Ampliar alcance a LATAM',
				diff: { before: '...', after: '...' },
				accepted: true,
			},
		],
		downstream_impact: [
			{
				id: 'imp_01KT...',
				phase: 'features',
				targetId: 'feat_01KT...',
				artifact_type: 'Feature',
				targetDisplayId: 'FEAT-02',
				targetTitle: 'Categorización inteligente de consumos',
				section: 'description',
				rationale:
					"Cambiaste 'Alcance del producto' en Descubrimiento §2.Esta característica hereda ese alcance.",
				diff: {
					field: 'description',
					before: 'viajes nacionales...',
					after: 'viajes y vuelos en LATAM...',
				},
				accepted: false,
			},
		],
	},
];

// MOCK IMPLEMENTATION

const mockCheckConsistency = async ({
	project_id,
	phase_origin,
	phase_destination,
	changes,
}: ConsistencyCheck): Promise<ConsistencyReportResponse> => {
	await delay(5000);
	return mockChecklistResponses[
		Math.floor(Math.random() * mockChecklistResponses.length)
	];
};

// REAL IMPLEMENTATION

const realCheckConsistency = async ({
	project_id,
	phase_origin,
	phase_destination,
	changes,
}: ConsistencyCheck): Promise<ConsistencyReportResponse> => {
	const data = await apiClient<BackendConsistencyReport>(
		`/api/v1/projects/${project_id}/consistency/evaluate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				phase_origin,
				phase_destination,
				changes,
			}),
		},
	);
	return {
		source_type: data.source_type as ConsistencyReportResponse['source_type'],
		source_id: data.source_id,
		target_type: (phase_destination || (data.downstream_impact?.[0]?.phase || 'features')) as ConsistencyReportResponse['target_type'],
		your_changes: (data.your_changes ?? []).map(mapChange),
		downstream_impact: (data.downstream_impact ?? []).map(mapImpact),
	};
};

export const checkConsistency = (params: ConsistencyCheck) => {
	return USE_MOCKS
		? mockCheckConsistency({
				...params,
			})
		: realCheckConsistency({
				...params,
			});
};

interface ApplyImpactPayload {
	artifact_type: string;
	target_id: string;
	action: string;
	field?: string;
	before?: string;
	after?: string;
}

interface ApplyConsistencyResult {
	applied: { target_id: string; artifact_type: string }[];
	failed: { target_id: string; artifact_type: string; reason: string }[];
}

export const applyConsistencyImpacts = async (
	project_id: string,
	impacts: DownstreamProposal[],
): Promise<ApplyConsistencyResult> => {
	const payloads: ApplyImpactPayload[] = [];
	for (const i of impacts) {
		if (!i.targetId || !i.artifact_type) continue;
		payloads.push({
			artifact_type: i.artifact_type,
			target_id: i.targetId,
			action: i.action || 'update',
			field: i.diff?.field,
			before: i.diff?.before,
			after: i.diff?.after,
		});
	}

	const data = await apiClient<ApplyConsistencyResult>(
		`/api/v1/projects/${project_id}/consistency/apply`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ impacts: payloads }),
		},
	);

	return data;
};
