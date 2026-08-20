import { create } from 'zustand';
import { fetchImplementation, generateImplementation } from '../api/api';
import { buildSummary } from '../api/api';
import type { ImplementationStatus, ImplementationSummary } from './types';

interface ImplementationStore {
	status: ImplementationStatus;
	summary: ImplementationSummary | null;
	progress: string | null;
	errorMessage: string | null;
	implementations: Record<string, boolean>;
	startGeneration: (
		featureId: string,
		featureTitle: string,
		featureDisplayId: string,
	) => Promise<void>;
	loadImplementation: (
		featureId: string,
		featureTitle: string,
		featureDisplayId: string,
	) => Promise<void>;
	reset: () => void;
}

export const useImplementationStore = create<ImplementationStore>()((set) => ({
	status: 'idle',
	summary: null,
	progress: null,
	errorMessage: null,
	implementations: {},

	startGeneration: async (featureId, featureTitle, featureDisplayId) => {
		set({
			status: 'generating',
			summary: null,
			progress: 'Preparando generación...',
			errorMessage: null,
		});
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
		} catch (error) {
			set({
				status: 'failed',
				progress: null,
				errorMessage:
					error instanceof Error ? error.message : 'Error desconocido durante la generación.',
			});
		}
	},

	loadImplementation: async (featureId, featureTitle, featureDisplayId) => {
		try {
			const record = await fetchImplementation(featureId);
			if (!record || record.status !== 'implemented') {
				return;
			}
			const summary = buildSummary(
				featureId,
				featureTitle,
				featureDisplayId,
				{ generated_files: record.generatedFiles, traceability_edges: 0 },
				record.updatedAt,
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
			// Sin registro o error de red: se deja sin marcar para permitir regenerar
		}
	},

	reset: () => set({ status: 'idle', summary: null, progress: null, errorMessage: null }),
}));

export const clearImplementationStore = () => {
	useImplementationStore.setState({
		status: 'idle',
		summary: null,
		progress: null,
		errorMessage: null,
		implementations: {},
	});
};
