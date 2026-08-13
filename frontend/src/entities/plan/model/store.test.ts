import { describe, it, expect, beforeEach } from 'vitest';
import { usePlanStore, clearPlanStore } from './store';
import type { PlanChange } from './types';

const makePlanChange = (overrides: Partial<PlanChange> & Pick<PlanChange, 'id'>): PlanChange => ({
	section: '§1 Default',
	description: 'Default description',
	diff: { before: '', after: '' },
	status: 'pending',
	origin: 'chat',
	phase: 'discovery',
	context: 'project-1',
	created_at: '2026-07-27T17:05:00Z',
	...overrides,
});

describe('usePlanStore — Plan de Cambios por Fase (T9)', () => {
	beforeEach(() => {
		clearPlanStore();
	});

	it('debe inicializar planByPhase como un objeto vacío', () => {
		const state = usePlanStore.getState();
		expect(state.planByPhase).toEqual({});
	});

	it('debe agregar un cambio al plan en una fase específica (addToPlan)', () => {
		const change = makePlanChange({
			id: 'chg_01',
			section: '§2 Alcance del producto',
			description: 'Ampliar alcance a LATAM',
			diff: { before: 'nacional', after: 'LATAM' },
			origin: 'Chat Descubrimiento',
		});

		usePlanStore.getState().addToPlan('discovery', change);

		const state = usePlanStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(1);
		expect(state.planByPhase['discovery'][0]).toEqual(change);
	});

	it('debe actualizar un cambio existente si se vuelve a agregar con el mismo ID (upsert)', () => {
		const change1 = makePlanChange({
			id: 'chg_01',
			section: '§2 Alcance',
			description: 'v1',
			diff: { before: 'a', after: 'b' },
		});
		const changeUpdated: PlanChange = { ...change1, status: 'accepted' };

		usePlanStore.getState().addToPlan('discovery', change1);
		usePlanStore.getState().addToPlan('discovery', changeUpdated);

		const state = usePlanStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(1);
		expect(state.planByPhase['discovery'][0].status).toBe('accepted');
	});

	it('debe remover un cambio del plan por su ID (removeFromPlan)', () => {
		const change = makePlanChange({
			id: 'chg_02',
			section: '§3 Monedas',
			description: 'Multimoneda',
			diff: { before: 'USD', after: 'USD, EUR' },
		});

		usePlanStore.getState().addToPlan('discovery', change);
		usePlanStore.getState().removeFromPlan('discovery', 'chg_02');

		const state = usePlanStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(0);
	});

	it('debe limpiar el plan de una fase (clearPlan)', () => {
		const change1 = makePlanChange({ id: 'chg_01', section: '§1', description: 'desc1' });
		const change2 = makePlanChange({ id: 'chg_02', section: '§2', description: 'desc2' });

		usePlanStore.getState().addToPlan('discovery', change1);
		usePlanStore.getState().addToPlan('discovery', change2);
		usePlanStore.getState().clearPlan('discovery');

		expect(usePlanStore.getState().planByPhase['discovery']).toEqual([]);
	});

	it('debe resetear todos los planes de todas las fases (clearPlanStore)', () => {
		const change = makePlanChange({ id: 'chg_01' });
		usePlanStore.getState().addToPlan('discovery', change);
		usePlanStore.getState().addToPlan('requirements', change);

		clearPlanStore();

		expect(usePlanStore.getState().planByPhase).toEqual({});
	});

	it('debe actualizar el estado y userVersion de un cambio (updatePlanChangeStatus)', () => {
		const change = makePlanChange({
			id: 'chg_03',
			section: '§5 Stakeholders',
			description: 'Actualizar roles',
			diff: { before: 'v1', after: 'v2' },
		});

		usePlanStore.getState().addToPlan('discovery', change);
		usePlanStore
			.getState()
			.updatePlanChangeStatus('discovery', 'chg_03', 'conflict', 'v1_manual');

		const state = usePlanStore.getState();
		expect(state.planByPhase['discovery'][0].status).toBe('conflict');
		expect(state.planByPhase['discovery'][0].userVersion).toBe('v1_manual');
	});
});
