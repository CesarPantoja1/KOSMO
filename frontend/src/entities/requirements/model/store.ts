import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { USE_MOCKS } from '@/shared/api/config';

interface RequirementsStore {
	hasRequirements: Record<string, boolean>;
	setHasRequirements: (id: string, has: boolean) => void;
}

export const isUsingMocks = () => USE_MOCKS;

export const useRequirementsStore = create<RequirementsStore>()(
	persist(
		(set) => ({
			hasRequirements: {},
			setHasRequirements: (id, has) =>
				set((state) => ({
					hasRequirements: { ...state.hasRequirements, [id]: has },
				})),
		}),
		{
			name: 'kosmo-requirements-store',
			partialize: (state) => ({ hasRequirements: state.hasRequirements }),
		},
	),
);
