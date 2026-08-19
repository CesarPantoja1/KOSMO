import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { generateImplementation } from '../api/api';
import type { ImplementationStatus, ImplementationSummary } from './types';

interface ImplementationStore {
	status: ImplementationStatus;
	summary: ImplementationSummary | null;
	progress: string | null;
	implementations: Record<string, boolean>;
	startGeneration: (
		featureId: string,
		featureTitle: string,
		featureDisplayId: string,
	) => Promise<void>;
	reset: () => void;
}

export const useImplementationStore = create<ImplementationStore>()(
	persist(
		(set) => ({
			status: 'idle',
			summary: null,
			progress: null,
			implementations: {},

			startGeneration: async (featureId, featureTitle, featureDisplayId) => {
				set({ status: 'generating', summary: null, progress: 'Preparando generación...' });
				try {
					const summary = await generateImplementation(
						featureId,
						featureTitle,
						featureDisplayId,
						(progress) => set({ progress }),
					);
					set((state) => ({
						status: 'completed',
						summary,
						progress: null,
						implementations: {
							...state.implementations,
							[featureId]: true,
						},
					}));
				} catch {
					set({ status: 'failed', progress: null });
				}
			},

			reset: () => set({ status: 'idle', summary: null, progress: null }),
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
		progress: null,
		implementations: {},
	});
};
