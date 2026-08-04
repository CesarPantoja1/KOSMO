import { create } from 'zustand';
import type { ConsistencyReportResponse } from './types';

interface ConsistencyStore {
	report: ConsistencyReportResponse | null;
	setReport: (report: ConsistencyReportResponse) => void;
	acceptChange: (changeId: string) => void;
	rejectChange: (changeId: string) => void;
	acceptImpact: (impactId: string) => void;
	rejectImpact: (impactId: string) => void;
	acceptAll: () => void;
	rejectAll: () => void;
	clearReport: () => void;
	resetConsistency: () => void;
	get hasPending(): boolean;
}

export const useConsistencyStore = create<ConsistencyStore>()((set, get) => ({
	report: null,

	get hasPending() {
		const { report } = get();
		if (!report) return false;
		const pendingChanges = report.your_changes.some((c) => !c.accepted);
		const pendingImpacts = report.downstream_impact.some((i) => !i.accepted);
		return pendingChanges || pendingImpacts;
	},

	setReport: (report) => set({ report }),

	acceptChange: (changeId) =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					your_changes: state.report.your_changes.map((c) =>
						c.change_id === changeId ? { ...c, accepted: true } : c,
					),
				},
			};
		}),

	rejectChange: (changeId) =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					your_changes: state.report.your_changes.map((c) =>
						c.change_id === changeId ? { ...c, accepted: false } : c,
					),
				},
			};
		}),

	acceptImpact: (impactId) =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					downstream_impact: state.report.downstream_impact.map((i) =>
						i.id === impactId ? { ...i, accepted: true } : i,
					),
				},
			};
		}),

	rejectImpact: (impactId) =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					downstream_impact: state.report.downstream_impact.map((i) =>
						i.id === impactId ? { ...i, accepted: false } : i,
					),
				},
			};
		}),

	acceptAll: () =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					your_changes: state.report.your_changes.map((c) => ({ ...c, accepted: true })),
					downstream_impact: state.report.downstream_impact.map((i) => ({
						...i,
						accepted: true,
					})),
				},
			};
		}),

	rejectAll: () =>
		set((state) => {
			if (!state.report) return state;
			return {
				report: {
					...state.report,
					your_changes: state.report.your_changes.map((c) => ({ ...c, accepted: false })),
					downstream_impact: state.report.downstream_impact.map((i) => ({
						...i,
						accepted: false,
					})),
				},
			};
		}),

	clearReport: () => set({ report: null }),

	resetConsistency: () => set({ report: null }),
}));
