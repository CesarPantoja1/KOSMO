import { apiClient } from './client';
import { USE_MOCKS } from './config';
import type { PlanChange } from '@/entities/plan/model/types';

export interface PlanStateViewResponse {
	project_id: string;
	phase: string;
	context_id?: string | null;
	changes: Array<{
		id: string;
		section: string;
		description: string;
		diff: {
			before: string;
			after: string;
		};
		status: 'pending' | 'accepted' | 'conflict' | 'discarded';
		origin?: string;
		rationale?: string | null;
		user_version?: string | null;
	}>;
}

const mapBackendToPlanChange = (
	item: PlanStateViewResponse['changes'][number],
	phase: string,
	context: string,
): PlanChange => ({
	id: item.id,
	section: item.section,
	description: item.description,
	diff: {
		before: item.diff.before,
		after: item.diff.after,
	},
	status: item.status,
	origin: item.origin ?? '',
	phase,
	context,
	rationale: item.rationale ?? undefined,
	userVersion: item.user_version ?? undefined,
	created_at: new Date().toISOString(),
});

export const planApi = {
	getPlanState: async (
		projectId: string,
		phase: string,
		contextId?: string,
	): Promise<PlanChange[]> => {
		if (USE_MOCKS) {
			return [];
		}
		const params = new URLSearchParams({ phase });
		if (contextId) {
			params.append('context', contextId);
		}
		const data = await apiClient<PlanStateViewResponse>(
			`/api/v1/projects/${projectId}/plan?${params.toString()}`,
		);
		return data.changes ? data.changes.map((item) => mapBackendToPlanChange(item, phase, contextId ?? '')) : [];
	},

	addPlanChange: async (
		projectId: string,
		phase: string,
		change: PlanChange,
		contextId?: string,
	): Promise<PlanChange[]> => {
		if (USE_MOCKS) {
			return [change];
		}
		const params = new URLSearchParams({ phase });
		if (contextId) {
			params.append('context', contextId);
		}
		const data = await apiClient<PlanStateViewResponse>(
			`/api/v1/projects/${projectId}/plan/changes?${params.toString()}`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					change_id: change.id,
					section: change.section,
					description: change.description,
					diff: change.diff,
					status: change.status,
					origin: change.origin,
					rationale: change.rationale,
				}),
			},
		);
		return data.changes ? data.changes.map((item) => mapBackendToPlanChange(item, phase, contextId ?? '')) : [];
	},

	deletePlanChange: async (
		projectId: string,
		phase: string,
		changeId: string,
	): Promise<void> => {
		if (USE_MOCKS) return;
		const params = new URLSearchParams({ phase });
		await apiClient<void>(
			`/api/v1/projects/${projectId}/plan/changes/${changeId}?${params.toString()}`,
			{
				method: 'DELETE',
			},
		);
	},

	discardPlan: async (
		projectId: string,
		phase: string,
		contextId?: string,
	): Promise<void> => {
		if (USE_MOCKS) return;
		const params = new URLSearchParams({ phase });
		if (contextId) {
			params.append('context', contextId);
		}
		await apiClient<void>(
			`/api/v1/projects/${projectId}/plan?${params.toString()}`,
			{
				method: 'DELETE',
			},
		);
	},
};
