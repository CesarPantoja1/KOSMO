import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { TraceabilityNavigationOutput } from '../model/types';

const mockGetTraceabilityNavigation = async (
	entityId: string,
	level: string,
): Promise<TraceabilityNavigationOutput> => {
	await new Promise((resolve) => setTimeout(resolve, 300));
	
	if (level === 'requisitos' || level === 'modelo') {
		return {
			permitted: false,
			redirect_message: `El requisito pertenece a una característica fuente. Para editarlo, dirígete a la vista de características.`,
			source_entity_name: 'Característica Origen',
			source_entity_id: entityId,
			source_level: 'caracteristicas',
		};
	}
	return { permitted: true };
};

const realGetTraceabilityNavigation = async (
	entityId: string,
	level: string,
): Promise<TraceabilityNavigationOutput> => {
	return apiClient<TraceabilityNavigationOutput>(
		`/api/v1/traceability/${entityId}/navigation?level=${level}`,
		{ method: 'GET' },
	);
};

export const getTraceabilityNavigation = (
	entityId: string,
	level: string,
): Promise<TraceabilityNavigationOutput> =>
	USE_MOCKS
		? mockGetTraceabilityNavigation(entityId, level)
		: realGetTraceabilityNavigation(entityId, level);
