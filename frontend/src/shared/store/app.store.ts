import { useState } from 'react';
import { create } from 'zustand';

interface AppState {
	initialized: boolean;
	setInitialized: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
	initialized: false,
	setInitialized: (v) => set({ initialized: v }),
}));

export const initializeProject = {
	id: 'prj_18932d32f480431ca6799211d9d4871d',
	name: 'Ferreteria',
	slug: 'ferreteria',
	description:
		'App integral para la gestión de inventario y sucursales para una ferreteria',
	owner_id: '43668b2b-79ac-4603-9b2b-cc385c150285',
	created_at: '2026-06-17T16:58:09.529601Z',
	updated_at: '2026-06-17T16:58:09.529606Z',
};

const [isProyectosOpen, setIsProyectosOpen] = useState(false);
