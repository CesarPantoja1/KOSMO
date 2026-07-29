import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { USE_MOCKS } from '@/shared/api/config';
import { planApi } from '@/shared/api/plan.api';
import type { PlanChange, PlanChangeStatus } from './types';

interface PlanStore {
	planByPhase: Record<string, PlanChange[]>;
	addToPlan: (phase: string, change: PlanChange) => void;
	removeFromPlan: (phase: string, changeId: string) => void;
	clearPlan: (phase: string) => void;
	updatePlanChangeStatus: (
		phase: string,
		changeId: string,
		status: PlanChangeStatus,
		userVersion?: string,
	) => void;
	setPhasePlan: (phase: string, changes: PlanChange[]) => void;
	fetchAndHydratePlan: (
		projectId: string,
		phase: string,
		contextId?: string,
	) => Promise<void>;
}

export const isUsingMocks = () => USE_MOCKS;

export const usePlanStore = create<PlanStore>()(
	persist(
		(set, get) => ({
			planByPhase: {},
			addToPlan: (phase, change) =>
				set((state) => {
					const currentList = state.planByPhase[phase] || [];
					const exists = currentList.some((item) => item.id === change.id);
					const newList = exists
						? currentList.map((item) => (item.id === change.id ? change : item))
						: [...currentList, change];
					return {
						planByPhase: {
							...state.planByPhase,
							[phase]: newList,
						},
					};
				}),
			removeFromPlan: (phase, changeId) =>
				set((state) => {
					const currentList = state.planByPhase[phase] || [];
					return {
						planByPhase: {
							...state.planByPhase,
							[phase]: currentList.filter((item) => item.id !== changeId),
						},
					};
				}),
			clearPlan: (phase) =>
				set((state) => ({
					planByPhase: {
						...state.planByPhase,
						[phase]: [],
					},
				})),
			updatePlanChangeStatus: (phase, changeId, status, userVersion) =>
				set((state) => {
					const currentList = state.planByPhase[phase] || [];
					return {
						planByPhase: {
							...state.planByPhase,
							[phase]: currentList.map((item) =>
								item.id === changeId
									? {
											...item,
											status,
											...(userVersion !== undefined ? { userVersion } : {}),
										}
									: item,
							),
						},
					};
				}),
			setPhasePlan: (phase, changes) =>
				set((state) => ({
					planByPhase: {
						...state.planByPhase,
						[phase]: changes,
					},
				})),
			fetchAndHydratePlan: async (projectId, phase, contextId) => {
				try {
					const backendChanges = await planApi.getPlanState(
						projectId,
						phase,
						contextId,
					);
					if (backendChanges) {
						get().setPhasePlan(phase, backendChanges);
					}
				} catch (err) {
					console.warn(
						`[usePlanStore] Error al hidratar plan desde backend para ${phase}:`,
						err,
					);
				}
			},
		}),
		{
			name: 'kosmo-plan-store',
			partialize: (state) => ({ planByPhase: state.planByPhase }),
		},
	),
);