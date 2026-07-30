import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface RequirementsStore {
	hasRequirements: Record<string, boolean>;
	setHasRequirements: (id: string, has: boolean) => void;
	resetRequirements: () => void;
}

export const useRequirementsStore = create<RequirementsStore>()(
	persist(
		(set) => ({
			hasRequirements: {},
				setHasRequirements: (id, has) =>
					set((state) => ({
						hasRequirements: { ...state.hasRequirements, [id]: has },
					})),
				resetRequirements: () => set({ hasRequirements: {} }),
		}),
		{
			name: 'kosmo-requirements-store',
			partialize: (state) => ({ hasRequirements: state.hasRequirements }),
		},
	),
);
