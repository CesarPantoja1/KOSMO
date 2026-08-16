import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { generateImplementation, getImplementationSummary } from '../api/api';
import type { ImplementationStatus, ImplementationSummary } from './types';

interface ImplementationStore {
	status: ImplementationStatus;
	summary: ImplementationSummary | null;
	implementations: Record<string, boolean>;
	startGeneration: (
		featureId: string,
		featureTitle: string,
		featureDisplayId: string,
	) => Promise<void>;
	completeGeneration: () => void;
	failGeneration: () => void;
	loadSummary: (featureId: string) => Promise<void>;
	setImplemented: (featureId: string, value: boolean) => void;
	reset: () => void;
}

export const useImplementationStore = create<ImplementationStore>()(
	persist(
		(set) => ({
			status: 'idle',
			summary: null,
			implementations: {},

			startGeneration: async (featureId, featureTitle, featureDisplayId) => {
				set({ status: 'generating', summary: null });
				try {
					const summary = await generateImplementation(
						featureId,
						featureTitle,
						featureDisplayId,
					);
					set((state) => ({
						status: 'completed',
						summary,
						implementations: {
							...state.implementations,
							[featureId]: true,
						},
					}));
				} catch {
					set({ status: 'failed' });
				}
			},

			completeGeneration: () => set({ status: 'completed' }),
			failGeneration: () => set({ status: 'failed' }),

			loadSummary: async (featureId) => {
				const summary = await getImplementationSummary(featureId);
				if (summary) {
					set({ summary });
				}
			},

			setImplemented: (featureId, value) =>
				set((state) => ({
					implementations: {
						...state.implementations,
						[featureId]: value,
					},
				})),

			reset: () => set({ status: 'idle', summary: null }),
		}),
		{
			name: 'kosmo-implementation-store',
			partialize: (state) => ({
				implementations: state.implementations,
			}),
		},
	),
);

export const clearImplementationStore = () => {
	useImplementationStore.persist.clearStorage();
	useImplementationStore.setState({
		status: 'idle',
		summary: null,
		implementations: {},
	});
};
