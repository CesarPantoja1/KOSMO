import { create } from 'zustand';
import { USE_MOCKS } from '@/shared/api/config';
import { apiClient } from '@/shared/api';
import type { SuggestCharacteristic, CharacteristicResponse } from './types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock data ---

const mockCharacteristics: CharacteristicResponse[] = [
	{
		id: '1',
		project_id: '',
		number: 1,
		title: 'Administración de Perfiles y Permisos de Usuario',
		slug: 'administracion-de-perfiles-y-permisos-de-usuario',
		description:
			'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
		origin: '',
		display_id: 'C01',
	},
	{
		id: '2',
		project_id: '',
		number: 2,
		title: 'Gestión de Inventario',
		slug: 'gestion-de-inventario',
		description:
			'Control de stock, entradas y salidas de productos, alertas de inventario bajo y registro de movimientos con trazabilidad.',
		origin: '',
		display_id: 'C02',
	},
	{
		id: '3',
		project_id: '',
		number: 3,
		title: 'Módulo de Ventas',
		slug: 'modulo-de-ventas',
		description:
			'Registro de ventas con cálculo automático de impuestos, descuentos y múltiples métodos de pago. Genera facturas electrónicas y tickets.',
		origin: '',
		display_id: 'C03',
	},
	{
		id: '4',
		project_id: '',
		number: 4,
		title: 'Reportes y Dashboard',
		slug: 'reportes-y-dashboard',
		description:
			'Visualización de indicadores clave como ventas diarias, productos más vendidos, márgenes de ganancia y tendencias de consumo.',
		origin: '',
		display_id: 'C04',
	},
];

const mockSuggestions: SuggestCharacteristic[] = [
	{
		number: 1,
		title: 'Notificaciones y Alertas',
		description:
			'Sistema de notificaciones push y por correo electrónico para alertar sobre eventos críticos como stock bajo, ventas grandes o vencimiento de productos.',
		origin: '',
	},
	{
		number: 2,
		title: 'Gestión de Clientes y Proveedores',
		description:
			'Registro y administración de clientes y proveedores con historial de compras, créditos, estados de cuenta y datos de contacto.',
		origin: '',
	},
	{
		number: 3,
		title: 'Módulo de Caja Diaria',
		description:
			'Apertura y cierre de caja, control de ingresos y egresos, arqueo de caja y conciliación con ventas del día.',
		origin: '',
	},
];

let mockStore = [...mockCharacteristics];

// --- Mock implementations ---

const mockGetCharacteristics = async (
	_projectId: string,
): Promise<CharacteristicResponse[]> => {
	await delay(800);
	return [...mockStore];
};

const mockGenerateCharacteristics = async (
	_projectId: string,
): Promise<CharacteristicResponse[]> => {
	await delay(2000);
	return [...mockStore];
};

const mockGetSuggestCharacteristics = async (
	_projectId: string,
): Promise<SuggestCharacteristic[]> => {
	await delay(800);
	return [...mockSuggestions];
};

const mockAddCharacteristic = async (
	projectId: string,
	item: {
		title: string;
		description: string;
	},
): Promise<CharacteristicResponse> => {
	await delay(600);
	const startNum = mockStore.length + 1;

	const newChar: CharacteristicResponse = {
		id: `mock-ID-${startNum}`,
		project_id: projectId,
		number: startNum,
		title: item.title,
		slug: 'slug-generated-from-title',
		description: item.description,
		origin: 'item origin',
		display_id: `C${String(startNum).padStart(2, '0')}`,
	};

	return newChar;
};

// --- Real API implementations ---

const realGetCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	const data = await apiClient<CharacteristicResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'GET' },
	);
	return data;
};

const realGenerateCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	const data = await apiClient<CharacteristicResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'POST' },
	);
	return data;
};

const realGetSuggestCharacteristics = async (
	projectId: string,
): Promise<SuggestCharacteristic[]> => {
	const data = await apiClient<SuggestCharacteristic[]>(
		`/api/v1/projects/${projectId}/features/suggest`,
		{ method: 'POST' },
	);
	return data;
};

const realAddCharacteristic = async (
	projectId: string,
	item: {
		title: string;
		description: string;
	},
): Promise<CharacteristicResponse> => {
	const data = await apiClient<CharacteristicResponse>(
		`/api/v1/projects/${projectId}/features/manual`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				title: item.title,
				description: item.description,
			}),
		},
	);
	return data;
};

// --- Store ---

interface CharacteristicStore {
	currentCharacteristics: CharacteristicResponse[];
	setCurrentCharacteristics: (characteristics: CharacteristicResponse[]) => void;
	currentSuggestions: SuggestCharacteristic[];
	setCurrentSuggestions: (suggestions: SuggestCharacteristic[]) => void;
	clearCharacteristics: () => void;
	getCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	generateCharacteristics: (projectId: string) => Promise<CharacteristicResponse[]>;
	getSuggestCharacteristics: (projectId: string) => Promise<SuggestCharacteristic[]>;
	addCharacteristic: (
		projectId: string,
		item: { title: string; description: string },
	) => Promise<CharacteristicResponse>;
}

export const useCharacteristicStore = create<CharacteristicStore>()((set) => ({
	currentCharacteristics: [],
	setCurrentCharacteristics: (characteristics) =>
		set({ currentCharacteristics: characteristics }),
	currentSuggestions: [],
	setCurrentSuggestions: (suggestions) => set({ currentSuggestions: suggestions }),
	clearCharacteristics: () =>
		set({ currentCharacteristics: [], currentSuggestions: [] }),

	getCharacteristics: async (projectId) => {
		const data = USE_MOCKS
			? await mockGetCharacteristics(projectId)
			: await realGetCharacteristics(projectId);
		set({ currentCharacteristics: data });
		return data;
	},

	generateCharacteristics: async (projectId) => {
		const data = USE_MOCKS
			? await mockGenerateCharacteristics(projectId)
			: await realGenerateCharacteristics(projectId);
		set({ currentCharacteristics: data });
		return data;
	},

	getSuggestCharacteristics: async (projectId) => {
		const data = USE_MOCKS
			? await mockGetSuggestCharacteristics(projectId)
			: await realGetSuggestCharacteristics(projectId);
		set({ currentSuggestions: data });
		return data;
	},

	addCharacteristic: async (projectId, item) => {
		const data = USE_MOCKS
			? await mockAddCharacteristic(projectId, item)
			: await realAddCharacteristic(projectId, item);
		set((state) => ({
			currentCharacteristics: [...state.currentCharacteristics, data],
		}));
		return data;
	},
}));