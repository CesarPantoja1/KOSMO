import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type {
	ApplyResponse,
	CollisionResponse,
	PlanChange,
	PlanResponse,
} from '../model/types';

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
	changeId: string,
): Promise<PlanResponse> => {
	await delay(600);
	// Buscar el cambio en todos los phases del mock
	for (const phase of Object.keys(mockPlanByPhase)) {
		const change = mockPlanByPhase[phase].find((c) => c.id === changeId);
		if (change) {
			return {
				phase,
				context: '',
				changes: mockPlanByPhase[phase],
				pending_count: mockPlanByPhase[phase].filter((c) => c.status === 'pending')
					.length,
				conflict_count: mockPlanByPhase[phase].filter((c) => c.status === 'conflict')
					.length,
			};
		}
	}
	// Si no existe, crear uno nuevo en discovery
	const newChange: PlanChange = {
		id: changeId,
		section: 'Nueva sección',
		description: 'Cambio agregado via mock',
		diff: { before: '', after: 'Contenido nuevo' },
		status: 'pending',
		origin: 'manual',
		phase: 'discovery',
		context: '',
		created_at: new Date().toISOString(),
	};
	mockPlanByPhase['discovery'] = [...(mockPlanByPhase['discovery'] ?? []), newChange];
	const list = mockPlanByPhase['discovery'];
	return {
		phase: 'discovery',
		context: '',
		changes: list,
		pending_count: list.filter((c) => c.status === 'pending').length,
		conflict_count: list.filter((c) => c.status === 'conflict').length,
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
		phase,
		context: '',
		changes: list,
		pending_count: list.filter((c) => c.status === 'pending').length,
		conflict_count: list.filter((c) => c.status === 'conflict').length,
	};
};

const mockCheckCollision = async (_projectId: string): Promise<CollisionResponse> => {
	await delay(800);
	return {
		has_collision: false,
		collisions: [],
	};
};

const mockApplyChanges = async (
	_projectId: string,
	changeIds: string[],
): Promise<ApplyResponse> => {
	await delay(1200);
	// Marcar como accepted en el mock state
	for (const phase of Object.keys(mockPlanByPhase)) {
		mockPlanByPhase[phase] = mockPlanByPhase[phase].map((c) =>
			changeIds.includes(c.id) ? { ...c, status: 'accepted' } : c,
		);
	}
	return {
		applied: changeIds.map((id) => ({ change_id: id, section: 'Mock section' })),
		failed: [],
		propagation: { affected_phases: [] },
	};
};

// --- Real implementations ---

const realGetPlan = async (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<PlanResponse> => {
	const params = new URLSearchParams({ phase });
	if (contextId) params.append('context', contextId);
	return apiClient<PlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan?${params.toString()}`,
		{ method: 'GET' },
	);
};

const realDiscardPlan = async (
	projectId: string,
	phase: string,
	contextId?: string,
): Promise<void> => {
	const params = new URLSearchParams({ phase });
	if (contextId) params.append('context', contextId);
	await apiClient<void>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan?${params.toString()}`,
		{ method: 'DELETE' },
	);
};

const realAddPlanChange = async (
	projectId: string,
	changeId: string,
): Promise<PlanResponse> =>
	apiClient<PlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/changes`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ change_id: changeId }),
		},
	);

const realDeletePlanChange = async (
	projectId: string,
	phase: string,
	changeId: string,
): Promise<PlanResponse> => {
	const params = new URLSearchParams({ phase });
	return apiClient<PlanResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/changes/${encodeURIComponent(changeId)}?${params.toString()}`,
		{ method: 'DELETE' },
	);
};

const realCheckCollision = async (projectId: string): Promise<CollisionResponse> =>
	apiClient<CollisionResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/collision-check`,
		{ method: 'POST' },
	);

const realApplyChanges = async (
	projectId: string,
	changeIds: string[],
): Promise<ApplyResponse> =>
	apiClient<ApplyResponse>(
		`/api/v1/projects/${encodeURIComponent(projectId)}/plan/apply`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ change_ids: changeIds }),
		},
	);

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
	changeId: string,
): Promise<PlanResponse> =>
	USE_MOCKS
		? mockAddPlanChange(projectId, changeId)
		: realAddPlanChange(projectId, changeId);

export const deletePlanChange = (
	projectId: string,
	phase: string,
	changeId: string,
): Promise<PlanResponse> =>
	USE_MOCKS
		? mockDeletePlanChange(projectId, phase, changeId)
		: realDeletePlanChange(projectId, phase, changeId);

export const checkPlanCollision = (projectId: string): Promise<CollisionResponse> =>
	USE_MOCKS ? mockCheckCollision(projectId) : realCheckCollision(projectId);

export const applyPlanChanges = (
	projectId: string,
	changeIds: string[],
): Promise<ApplyResponse> =>
	USE_MOCKS
		? mockApplyChanges(projectId, changeIds)
		: realApplyChanges(projectId, changeIds);
