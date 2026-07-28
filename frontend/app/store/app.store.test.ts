import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from './app.store';
import type { PlanChange } from '@/entities/plan/model/types';

describe('useAppStore — Plan Persistence & Actions (T9)', () => {
	beforeEach(() => {
		useAppStore.getState().resetProjectState();
	});

	it('debe inicializar planByPhase como un objeto vacío', () => {
		const state = useAppStore.getState();
		expect(state.planByPhase).toEqual({});
	});

	it('debe agregar un cambio al plan en una fase específica (addToPlan)', () => {
		const change: PlanChange = {
			id: 'chg_01',
			section: '§2 Alcance del producto',
			description: 'Ampliar alcance a LATAM',
			diff: { before: 'nacional', after: 'LATAM' },
			status: 'pending',
			origin: 'Chat Descubrimiento',
		};

		useAppStore.getState().addToPlan('discovery', change);

		const state = useAppStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(1);
		expect(state.planByPhase['discovery'][0]).toEqual(change);
	});

	it('debe actualizar un cambio existente si se vuelve a agregar con el mismo ID', () => {
		const change1: PlanChange = {
			id: 'chg_01',
			section: '§2 Alcance',
			description: 'v1',
			diff: { before: 'a', after: 'b' },
			status: 'pending',
		};

		const changeUpdated: PlanChange = {
			...change1,
			status: 'accepted',
		};

		useAppStore.getState().addToPlan('discovery', change1);
		useAppStore.getState().addToPlan('discovery', changeUpdated);

		const state = useAppStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(1);
		expect(state.planByPhase['discovery'][0].status).toBe('accepted');
	});

	it('debe remover un cambio del plan por su ID (removeFromPlan)', () => {
		const change: PlanChange = {
			id: 'chg_02',
			section: '§3 Monedas',
			description: 'Multimoneda',
			diff: { before: 'USD', after: 'USD, EUR' },
			status: 'pending',
		};

		useAppStore.getState().addToPlan('discovery', change);
		useAppStore.getState().removeFromPlan('discovery', 'chg_02');

		const state = useAppStore.getState();
		expect(state.planByPhase['discovery']).toHaveLength(0);
	});

	it('debe limpiar el plan de una fase (clearPlan)', () => {
		const change1: PlanChange = {
			id: 'chg_01',
			section: '§1',
			description: 'desc1',
			diff: { before: '', after: '' },
			status: 'pending',
		};
		const change2: PlanChange = {
			id: 'chg_02',
			section: '§2',
			description: 'desc2',
			diff: { before: '', after: '' },
			status: 'pending',
		};

		useAppStore.getState().addToPlan('discovery', change1);
		useAppStore.getState().addToPlan('discovery', change2);
		useAppStore.getState().clearPlan('discovery');

		const state = useAppStore.getState();
		expect(state.planByPhase['discovery']).toEqual([]);
	});

	it('debe actualizar el estado y userVersion de un cambio (updatePlanChangeStatus)', () => {
		const change: PlanChange = {
			id: 'chg_03',
			section: '§5 Stakeholders',
			description: 'Actualizar roles',
			diff: { before: 'v1', after: 'v2' },
			status: 'pending',
		};

		useAppStore.getState().addToPlan('discovery', change);
		useAppStore.getState().updatePlanChangeStatus('discovery', 'chg_03', 'conflict', 'v1_manual');

		const state = useAppStore.getState();
		expect(state.planByPhase['discovery'][0].status).toBe('conflict');
		expect(state.planByPhase['discovery'][0].userVersion).toBe('v1_manual');
	});
});
