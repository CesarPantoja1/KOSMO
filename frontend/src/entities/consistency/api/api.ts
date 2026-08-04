import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import { ConsistencyCheck, ConsistencyReportResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

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
				targetId: 'feat_01KT...',
				targetDisplayId: 'FEAT-02',
				targetTitle: 'Categorización inteligente de consumos',
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
	return apiClient<ConsistencyReportResponse>(
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
