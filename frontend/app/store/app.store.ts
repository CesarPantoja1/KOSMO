import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from '@/entities/project/model/types';
import type { PlanChange, PlanChangeStatus } from '@/entities/plan/model/types';
import { planApi } from '@/shared/api/plan.api';

interface AppState {
	initialized: boolean;
	setInitialized: (v: boolean) => void;
	currentProject: Project | null;
	setCurrentProject: (project: Project) => void;
	clearCurrentProject: () => void;
	setProjectState: (project: Project) => void;
	resetProjectState: () => void;
	isProyectosOpen: boolean;
	setIsProyectosOpen: (v: boolean) => void;
	hasUnsavedChanges: boolean;
	setHasUnsavedChanges: (v: boolean) => void;
	pendingNavigationPath: string | null;
	setPendingNavigationPath: (v: string | null) => void;
	isEditorMaximized: boolean;
	setEditorMaximized: (v: boolean) => void;

	// Sprint 4 — Plan de Cambios por Fase ("discovery" | "characteristics" | "requirements")
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

export const useAppStore = create<AppState>()(
	persist(
		(set, get) => ({
			initialized: false,
			setInitialized: (v) => set({ initialized: v }),
			currentProject: null,
			setCurrentProject: (project) => set({ currentProject: project }),
			clearCurrentProject: () => set({ currentProject: null, isProyectosOpen: false }),
			setProjectState: (project) =>
				set({ currentProject: project, isProyectosOpen: true }),
			resetProjectState: () =>
				set({
					currentProject: null,
					isProyectosOpen: false,
					hasUnsavedChanges: false,
					pendingNavigationPath: null,
					planByPhase: {},
				}),
			isProyectosOpen: false,
			setIsProyectosOpen: (v) => set({ isProyectosOpen: v }),
			hasUnsavedChanges: false,
			setHasUnsavedChanges: (v) => set({ hasUnsavedChanges: v }),
			pendingNavigationPath: null,
			setPendingNavigationPath: (v) => set({ pendingNavigationPath: v }),
			isEditorMaximized: false,
			setEditorMaximized: (v) => set({ isEditorMaximized: v }),

			// Sprint 4 — Plan de Cambios
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
						`[useAppStore] Error al hidratar plan desde backend para ${phase}:`,
						err,
					);
				}
			},
		}),
		{
			name: 'kosmo-app-store',
			partialize: (state) => ({
				currentProject: state.currentProject,
				isProyectosOpen: state.isProyectosOpen,
				planByPhase: state.planByPhase,
			}),
		},
	),
);
