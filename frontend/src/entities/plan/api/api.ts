import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type {
	ApplyResponse,
	PlanChange,
	PlanResponse,
} from '../model/types';

const BACKEND_PHASE: Record<string, string> = {
	discovery: 'descubrimiento',
	features: 'caracteristicas',
	requirements: 'requisitos',
};

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---
const mockPlanByPhase: Record<string, PlanChange[]> = {
	discovery: [
		{
			id: 'chg_mock_001',
			section: '1 Introducción',
			description: 'Actualizar descripción del proyecto para incluir nuevos objetivos',
			diff: {
				before: '## Introducción\n\nEste proyecto busca optimizar procesos.',
				after:
					'## Introducción\n\nEste proyecto busca optimizar procesos y reducir costos operativos en un 30%.',
			},
			status: 'pending',
			origin: 'chat',
			phase: 'discovery',
			context: '',
			rationale: 'El cliente solicitó incluir el objetivo de reducción de costos.',
			created_at: '2026-07-27T17:05:00Z',
		},
		{
			id: 'chg_mock_002',
			section: '2 Alcance del producto',
			description: 'Ampliar el alcance para incluir integración con sistemas legacy',
			diff: {
				before: '### Incluido\n- Viajes LATAM\n### Excluido\n- Viajes intercontinentales',
				after:
					'### Incluido\n- Viajes LATAM\n- Integración con sistemas legacy\n### Excluido\n- Viajes intercontinentales',
			},
			status: 'conflict',
			origin: 'chat',
			phase: 'discovery',
			context: '',
			rationale: 'Se identificó dependencia con sistemas existentes del cliente.',
			created_at: '2026-07-27T17:10:00Z',
		},
	],
};

// --- Mock implementations ---

const mockGetPlan = async (
	_projectId: string,
	phase: string,
	_contextId?: string,
): Promise<PlanResponse> => {
	await delay(400);
	const changes = mockPlanByPhase[phase] ?? [];
	return {
		project_id: _projectId,
		phase,
		context: _contextId ?? '',
		changes,
		pending_count: changes.filter((c) => c.status === 'pending').length,
		conflict_count: changes.filter((c) => c.status === 'conflict').length,
	};
};

const mockDiscardPlan = async (
	_projectId: string,
	phase: string,
	_contextId?: string,
): Promise<void> => {
	await delay(500);
	mockPlanByPhase[phase] = [];
};

const mockAddPlanChange = async (
	_projectId: string,
	phase: string,
	change: PlanChange,
): Promise<PlanResponse> => {
	await delay(600);
	const existing = mockPlanByPhase[phase] ?? [];
	const idx = existing.findIndex((c) => c.id === change.id);
	const updated = idx >= 0
		? existing.map((c, i) => (i === idx ? change : c))
		: [...existing, change];
	mockPlanByPhase[phase] = updated;
	return {
		project_id: _projectId,
		phase,
		context: '',
		changes: updated,
		pending_count: updated.filter((c) => c.status === 'pending').length,
		conflict_count: updated.filter((c) => c.status === 'conflict').length,
	};
};

const mockDeletePlanChange = async (
	_projectId: string,
	phase: string,
	changeId: string,
): Promise<PlanResponse> => {
	await delay(400);
	const list = (mockPlanByPhase[phase] ?? []).filter((c) => c.id !== changeId);
	mockPlanByPhase[phase] = list;
	return {
		project_id: _projectId,
		phase,
		context: '',
		changes: list,
		pending_count: list.filter((c) => c.status === 'pending').length,
		conflict_count: list.filter((c) => c.status === 'conflict').length,
	};
};

const mockApplyChanges = async (
	_projectId: string,
	changeIds: string[],
): Promise<ApplyResponse> => {
	await delay(1200);
	const failed_changes: { id: string; reason: string }[] = [];
	for (const phase of Object.keys(mockPlanByPhase)) {
		const list = mockPlanByPhase[phase];
		if (!list) continue;
		const applied = list.filter((c) => changeIds.includes(c.id) && c.status !== 'conflict');
		const failed = list.filter((c) => changeIds.includes(c.id) && c.status === 'conflict');
		for (const f of failed) {
			failed_changes.push({ id: f.id, reason: 'El fragmento original ya no se encuentra en el documento' });
		}
		mockPlanByPhase[phase] = list
			.filter((c) => !changeIds.includes(c.id))
			.concat(applied.map((c) => ({ ...c, status: 'applied' as const })));
	}
	return {
		applied_count: changeIds.length - failed_changes.length,
		failed_count: failed_changes.length,
		failed_changes,
		propagation: null,
	};
};

// --- Real implementations ---

function mapBackendPhase(frontendPhase: string): string {
	return BACKEND_PHASE[frontendPhase] ?? frontendPhase;
}

interface BackendPlanResponse {
	project_id: string;
	phase: string;
	context: string;
	changes: Array<{
		id: string;
		section: string;
		description: string;
		diff: { before: string; after: string };
		status: string;
		origin: string;
		rationale?: string | null;
		user_version?: string | null;
	}>;
	pending_count: number;
	conflict_count: number;
}

function mapBackendChange(item: BackendPlanResponse['changes'][number], frontendPhase: string, context: string): PlanChange {
	return {
		id: item.id,
		section: item.section,
		description: item.description,
		diff: { before: item.diff.before, after: item.diff.after },
		status: item.status as PlanChange['status'],
		origin: item.origin ?? '',
		phase: frontendPhase,
		context: context ?? '',
		rationale: item.rationale ?? undefined,
		userVersion: item.user_version ?? undefined,
		created_at: new Date().toISOString(),
	};
}

const realGetPlan = async (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<PlanResponse> => {
	const params = new URLSearchParams({ phase: mapBackendPhase(phase) });
	if (contextId) params.append('context', contextId);
	const data = await apiClient<BackendPlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan?${params.toString()}`,
		{ method: 'GET' },
	);
	const mappedChanges = (data.changes ?? []).map((item) =>
		mapBackendChange(item, phase, data.context ?? ''),
	);
	return {
		project_id: data.project_id,
		phase,
		context: data.context ?? '',
		changes: mappedChanges,
		pending_count: data.pending_count,
		conflict_count: data.conflict_count,
	};
};

const realDiscardPlan = async (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<void> => {
	const params = new URLSearchParams({ phase: mapBackendPhase(phase) });
	if (contextId) params.append('context', contextId);
	await apiClient<void>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan?${params.toString()}`,
		{ method: 'DELETE' },
	);
};

const realAddPlanChange = async (
	projectId: string,
	phase: string,
	change: PlanChange,
): Promise<PlanResponse> => {
	const params = new URLSearchParams({ phase: mapBackendPhase(phase) });
	const data = await apiClient<BackendPlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/changes?${params.toString()}`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				change_id: change.id,
				section: change.section,
				description: change.description,
				diff_before: change.diff.before,
				diff_after: change.diff.after,
				rationale: change.rationale,
			}),
		},
	);
	const mappedChanges = (data.changes ?? []).map((item) =>
		mapBackendChange(item, phase, data.context ?? ''),
	);
	return {
		project_id: data.project_id,
		phase,
		context: data.context ?? '',
		changes: mappedChanges,
		pending_count: data.pending_count,
		conflict_count: data.conflict_count,
	};
};

const realDeletePlanChange = async (
	projectId: string,
	phase: string,
	changeId: string,
): Promise<PlanResponse> => {
	const params = new URLSearchParams({ phase: mapBackendPhase(phase) });
	const data = await apiClient<BackendPlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/changes/${encodeURIComponent(changeId)}?${params.toString()}`,
		{ method: 'DELETE' },
	);
	const mappedChanges = (data.changes ?? []).map((item) =>
		mapBackendChange(item, phase, data.context ?? ''),
	);
	return {
		project_id: data.project_id,
		phase,
		context: data.context ?? '',
		changes: mappedChanges,
		pending_count: data.pending_count,
		conflict_count: data.conflict_count,
	};
};

interface BackendApplyResponse {
	applied_count: number;
	failed_count: number;
	failed_changes: Array<{ id: string; reason: string }>;
	propagation: { affected_phases: Array<{ phase: string; affected_count: number; affected_ids: string[] }> } | null;
}

const realApplyChanges = async (
	projectId: string,
	phase: string,
	changeIds: string[],
): Promise<ApplyResponse> => {
	const data = await apiClient<BackendApplyResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/apply`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				phase: mapBackendPhase(phase),
				changes: changeIds,
			}),
		},
	);
	return {
		applied_count: data.applied_count,
		failed_count: data.failed_count,
		failed_changes: data.failed_changes ?? [],
		propagation: data.propagation ?? null,
	};
};

// --- Exports (switch based on USE_MOCKS) ---

export const getPlan = (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<PlanResponse> =>
	USE_MOCKS
		? mockGetPlan(projectId, phase, contextId)
		: realGetPlan(projectId, phase, contextId);

export const discardPlan = (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<void> =>
	USE_MOCKS
		? mockDiscardPlan(projectId, phase, contextId)
		: realDiscardPlan(projectId, phase, contextId);

export const addPlanChange = (
	projectId: string,
	phase: string,
	change: PlanChange,
): Promise<PlanResponse> =>
	USE_MOCKS
		? mockAddPlanChange(projectId, phase, change)
		: realAddPlanChange(projectId, phase, change);

export const deletePlanChange = (
	projectId: string,
	phase: string,
	changeId: string,
): Promise<PlanResponse> =>
	USE_MOCKS
		? mockDeletePlanChange(projectId, phase, changeId)
		: realDeletePlanChange(projectId, phase, changeId);

export const applyPlanChanges = (
	projectId: string,
	phase: string,
	changeIds: string[],
): Promise<ApplyResponse> =>
	USE_MOCKS
		? mockApplyChanges(projectId, changeIds)
		: realApplyChanges(projectId, phase, changeIds);
