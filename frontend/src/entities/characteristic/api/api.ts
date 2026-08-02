import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type {
	SuggestCharacteristic,
	CharacteristicResponse,
	CharacteristicChatResponse,
} from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock data ---

const mockCharacteristics: CharacteristicResponse[] = [
	{
		id: '1',
		project_id: 'mock-project-1',
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
		project_id: 'mock-project-1',
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
		project_id: 'mock-project-1',
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
		project_id: 'mock-project-1',
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

const mockChatResponses: CharacteristicChatResponse[] = [
	{
		id: 'mock-chat-1',
		role: 'assistant',
		content: 'Hola, ¿en qué puedo ayudarte con la característica?',
		created_at: new Date().toISOString(),
		change_suggestions: null,
	},
	{
		id: 'mock-chat-2',
		role: 'assistant',
		content:
			'Aquí tienes una sugerencia de cambio para mejorar la descripción de la característica.',
		created_at: new Date().toISOString(),
		change_suggestions: [{
			id: 'mock-change-1',
			section: 'Descripción de la característica',
			description: 'Refinar la descripción para mayor claridad.',
			diff_before:
				'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
			diff_after:
				'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para controlar el acceso a pantallas y funciones críticas del sistema.',
			rationale:
				'Se mejoró la claridad y precisión de la descripción de la característica.',
		}],
	},
	{
		id: 'mock-chat-3',
		role: 'assistant',
		content:
			'Aquí tienes una sugerencia de cambio para mejorar la descripción de la característica.',
		created_at: new Date().toISOString(),
		change_suggestions: [{
			id: 'mock-change-1',
			section: 'Descripción de la característica',
			description: 'Refinar la descripción para mayor claridad.',
			diff_before:
				'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
			diff_after:
				'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para controlar el acceso a pantallas y funciones críticas del sistema.',
			rationale:
				'Se mejoró la claridad y precisión de la descripción de la característica.',
		}],
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
	item: { title: string; description: string },
): Promise<CharacteristicResponse> => {
	await delay(600);
	const nextNum = mockStore.length + 1;
	const newChar: CharacteristicResponse = {
		id: `mock-ID-${nextNum}`,
		project_id: projectId,
		number: nextNum,
		title: item.title,
		slug: 'slug-generated-from-title',
		description: item.description,
		origin: 'item origin',
		display_id: `C${String(nextNum).padStart(2, '0')}`,
	};
	mockStore = [...mockStore, newChar];
	return newChar;
};

const mockSendChatMessage = async (
	_featureId: string,
	_content: string,
): Promise<CharacteristicChatResponse> => {
	await delay(500);
	return mockChatResponses[Math.floor(Math.random() * mockChatResponses.length)];
};

// --- Real implementations ---

const realGetCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	return apiClient<CharacteristicResponse[]>(`/api/v1/projects/${projectId}/features`, {
		method: 'GET',
	});
};

const realGenerateCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	return apiClient<CharacteristicResponse[]>(`/api/v1/projects/${projectId}/features`, {
		method: 'POST',
	});
};

const realGetSuggestCharacteristics = async (
	projectId: string,
): Promise<SuggestCharacteristic[]> => {
	return apiClient<SuggestCharacteristic[]>(
		`/api/v1/projects/${projectId}/features/suggest`,
		{ method: 'POST' },
	);
};

const realAddCharacteristic = async (
	projectId: string,
	item: { title: string; description: string },
): Promise<CharacteristicResponse> => {
	return apiClient<CharacteristicResponse>(
		`/api/v1/projects/${projectId}/features/manual`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ title: item.title, description: item.description }),
		},
	);
};

const realSendChatMessage = async (
	featureId: string,
	content: string,
): Promise<CharacteristicChatResponse> => {
	return apiClient<CharacteristicChatResponse>(`/api/v1/features/${featureId}/chat`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ content }),
	});
};

// --- Exports (switch based on USE_MOCKS) ---

export const getCharacteristics = (
	projectId: string,
): Promise<CharacteristicResponse[]> =>
	USE_MOCKS ? mockGetCharacteristics(projectId) : realGetCharacteristics(projectId);

export const generateCharacteristics = (
	projectId: string,
): Promise<CharacteristicResponse[]> =>
	USE_MOCKS
		? mockGenerateCharacteristics(projectId)
		: realGenerateCharacteristics(projectId);

export const getSuggestCharacteristics = (
	projectId: string,
): Promise<SuggestCharacteristic[]> =>
	USE_MOCKS
		? mockGetSuggestCharacteristics(projectId)
		: realGetSuggestCharacteristics(projectId);

export const addCharacteristic = (
	projectId: string,
	item: { title: string; description: string },
): Promise<CharacteristicResponse> =>
	USE_MOCKS
		? mockAddCharacteristic(projectId, item)
		: realAddCharacteristic(projectId, item);

export const sendChatMessage = (
	featureId: string,
	content: string,
): Promise<CharacteristicChatResponse> =>
	USE_MOCKS
		? mockSendChatMessage(featureId, content)
		: realSendChatMessage(featureId, content);
