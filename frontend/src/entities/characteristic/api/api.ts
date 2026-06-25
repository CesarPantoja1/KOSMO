import { apiClient } from '@/shared/api';
import { USE_CHARACTERISTIC_MOCKS } from '../config';
import type { AlternativeCharacteristic, Characteristic } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockCharacteristics: Characteristic[] = [
	{
		id: '1',
		project_id: '',
		number: 1,
		title: 'Administración de Perfiles y Permisos de Usuario',
		slug: 'administracion-de-perfiles-y-permisos-de-usuario',
		description:
			'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
		rationale: '',
		inferred_from: [],
		display_id: 'C01',
		requirements:
			'## Ubiquitous\n' +
			'- The system shall always require authentication before granting access to any module.\n' +
			'- The system shall always allow administrators to create, edit, and deactivate user accounts.\n\n' +
			'## State-driven\n' +
			'- While a user account is active, the system shall enforce the assigned role permissions on every request.\n\n' +
			'## Event-driven\n' +
			'- When a user submits login credentials, the system shall validate them against the stored hash and return a session token within 2 seconds.\n\n' +
			'## Unwanted behaviour\n' +
			'- If three consecutive failed login attempts occur, the system shall temporarily lock the account for 15 minutes.',
	},
	{
		id: '2',
		project_id: '',
		number: 2,
		title: 'Gestión de Inventario',
		slug: 'gestion-de-inventario',
		description:
			'Control de stock, entradas y salidas de productos, alertas de inventario bajo y registro de movimientos con trazabilidad.',
		rationale: '',
		inferred_from: [],
		display_id: 'C02',
		requirements: '',
	},
	{
		id: '3',
		project_id: '',
		number: 3,
		title: 'Módulo de Ventas',
		slug: 'modulo-de-ventas',
		description:
			'Registro de ventas con cálculo automático de impuestos, descuentos y múltiples métodos de pago. Genera facturas electrónicas y tickets.',
		rationale: '',
		inferred_from: [],
		display_id: 'C03',
		requirements: '',
	},
	{
		id: '4',
		project_id: '',
		number: 4,
		title: 'Reportes y Dashboard',
		slug: 'reportes-y-dashboard',
		description:
			'Visualización de indicadores clave como ventas diarias, productos más vendidos, márgenes de ganancia y tendencias de consumo.',
		rationale: '',
		inferred_from: [],
		display_id: 'C04',
		requirements: '',
	},
];

const mockSuggestions: AlternativeCharacteristic[] = [
	{
		id: 'sug_1',
		number: 1,
		title: 'Notificaciones y Alertas',
		description:
			'Sistema de notificaciones push y por correo electrónico para alertar sobre eventos críticos como stock bajo, ventas grandes o vencimiento de productos.',
		rationale: '',
		inferred_from: [],
	},
	{
		id: 'sug_2',
		number: 2,
		title: 'Gestión de Clientes y Proveedores',
		description:
			'Registro y administración de clientes y proveedores con historial de compras, créditos, estados de cuenta y datos de contacto.',
		rationale: '',
		inferred_from: [],
	},
	{
		id: 'sug_3',
		number: 3,
		title: 'Módulo de Caja Diaria',
		description:
			'Apertura y cierre de caja, control de ingresos y egresos, arqueo de caja y conciliación con ventas del día.',
		rationale: '',
		inferred_from: [],
	},
];

let mockStore = [...mockCharacteristics];

//
// MOCK implementations
//

const mockGetCharacteristics = async (
	_projectId: string,
): Promise<Characteristic[]> => {
	await delay(800);
	return [...mockStore];
};

const mockGenerateCharacteristics = async (
	_projectId: string,
): Promise<Characteristic[]> => {
	await delay(2000);
	return [...mockStore];
};

const mockGetAlternativeCharacteristics = async (
	_projectId: string,
): Promise<AlternativeCharacteristic[]> => {
	await delay(800);
	return [...mockSuggestions];
};

const mockAddCharacteristics = async (
	_projectId: string,
	items: { title: string; description: string; rationale: string; inferred_from?: string[] }[],
): Promise<Characteristic[]> => {
	await delay(600);
	const startNum = mockStore.length + 1;
	const newChars: Characteristic[] = items.map((item, i) => ({
		id: String(Date.now() + i),
		project_id: _projectId,
		number: startNum + i,
		title: item.title,
		slug: item.title.toLowerCase().replace(/\s+/g, '-'),
		description: item.description,
		rationale: item.rationale,
		inferred_from: item.inferred_from ?? [],
		display_id: `C${String(startNum + i).padStart(2, '0')}`,
		requirements: '',
	}));
	mockStore = [...mockStore, ...newChars];
	return newChars;
};

const mockSaveCharacteristicRequirements = async (
	_projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await delay(500);
	const idx = mockStore.findIndex((c) => c.id === characteristicId);
	if (idx !== -1) {
		mockStore[idx] = { ...mockStore[idx], requirements: content };
	}
};

const mockGenerateCharacteristicRequirements = async (
	_projectId: string,
	_characteristicId: string,
): Promise<string> => {
	await delay(2000);
	return (
		'## EARS Requirements\n\n' +
		'**Ubiquitous**\n' +
		'- The system shall always log every create, update, and delete operation with timestamp and user ID.\n' +
		'- The system shall always ensure data consistency across all related entities.\n\n' +
		'**State-driven**\n' +
		'- While the module is active, the system shall validate all input data against business rules before persisting.\n\n' +
		'**Event-driven**\n' +
		'- When a user triggers a data export, the system shall generate the file in the requested format within 5 seconds.\n\n' +
		'**Unwanted behaviour**\n' +
		'- If a network timeout occurs during a write operation, the system shall roll back the transaction and notify the user.'
	);
};

const mockGetCharacteristicRequirements = async (
	_projectId: string,
	characteristicId: string,
): Promise<string> => {
	await delay(400);
	const found = mockStore.find((c) => c.id === characteristicId);
	return found?.requirements ?? '';
};

//
// REAL API implementations
//

interface FeatureResponse {
	id: string;
	project_id: string;
	number: number;
	title: string;
	slug: string;
	description: string;
	rationale: string;
	inferred_from: string[];
	display_id: string;
}

interface FeatureSuggestionResponse {
	number: number;
	title: string;
	description: string;
	rationale: string;
	inferred_from: string[];
}

const mapFeatureResponse = (f: FeatureResponse): Characteristic => ({
	id: f.id,
	project_id: f.project_id,
	number: f.number,
	title: f.title,
	slug: f.slug,
	description: f.description,
	rationale: f.rationale,
	inferred_from: f.inferred_from,
	display_id: f.display_id,
	requirements: '',
});

const mapSuggestionResponse = (s: FeatureSuggestionResponse, _index: number): AlternativeCharacteristic => ({
	id: `sug_${s.number}`,
	number: s.number,
	title: s.title,
	description: s.description,
	rationale: s.rationale,
	inferred_from: s.inferred_from,
});

const realGetCharacteristics = async (
	projectId: string,
): Promise<Characteristic[]> => {
	const data = await apiClient<FeatureResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'GET' },
	);
	return data.map(mapFeatureResponse);
};

const realGenerateCharacteristics = async (
	projectId: string,
): Promise<Characteristic[]> => {
	const data = await apiClient<FeatureResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'POST' },
	);
	return data.map(mapFeatureResponse);
};

const realGetAlternativeCharacteristics = async (
	projectId: string,
): Promise<AlternativeCharacteristic[]> => {
	const data = await apiClient<FeatureSuggestionResponse[]>(
		`/api/v1/projects/${projectId}/features/suggest`,
		{ method: 'POST' },
	);
	return data.map(mapSuggestionResponse);
};

const realAddCharacteristics = async (
	projectId: string,
	items: { title: string; description: string; rationale: string; inferred_from?: string[] }[],
): Promise<Characteristic[]> => {
	const data = await apiClient<FeatureResponse[]>(
		`/api/v1/projects/${projectId}/features/save`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				features: items.map((item) => ({
					title: item.title,
					description: item.description,
					rationale: item.rationale,
					inferred_from: item.inferred_from ?? [],
				})),
			}),
		},
	);
	return data.map(mapFeatureResponse);
};

interface GenerateRequirementsResponse {
	feature_id: string;
	feature_number: number;
	requirements_markdown: string;
	total: number;
}

const realSaveCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await apiClient<{ feature_id: string; message: string }>(
		`/api/v1/features/${characteristicId}/requirements`,
		{
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId, markdown: content }),
		},
	);
};

const realGenerateCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	const data = await apiClient<GenerateRequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements/generate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId }),
		},
	);
	return data.requirements_markdown;
};

interface GetRequirementsResponse {
	document_markdown: string;
}

const realGetCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	const data = await apiClient<GetRequirementsResponse>(
		`/api/v1/features/${characteristicId}/requirements?project_id=${encodeURIComponent(projectId)}`,
		{ method: 'GET' },
	);
	return data.document_markdown;
};

//
// Exported functions (switch based on config)
//

const isUsingMocks = () => USE_CHARACTERISTIC_MOCKS;

export const getCharacteristics = async (
	projectId: string,
): Promise<Characteristic[]> => {
	return isUsingMocks()
		? mockGetCharacteristics(projectId)
		: realGetCharacteristics(projectId);
};

export const generateCharacteristics = async (
	projectId: string,
): Promise<Characteristic[]> => {
	return isUsingMocks()
		? mockGenerateCharacteristics(projectId)
		: realGenerateCharacteristics(projectId);
};

export const getAlternativeCharacteristics = async (
	projectId: string,
): Promise<AlternativeCharacteristic[]> => {
	return isUsingMocks()
		? mockGetAlternativeCharacteristics(projectId)
		: realGetAlternativeCharacteristics(projectId);
};

export const addCharacteristics = async (
	projectId: string,
	items: { title: string; description: string; rationale: string; inferred_from?: string[] }[],
): Promise<Characteristic[]> => {
	return isUsingMocks()
		? mockAddCharacteristics(projectId, items)
		: realAddCharacteristics(projectId, items);
};

export const saveCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	return isUsingMocks()
		? mockSaveCharacteristicRequirements(projectId, characteristicId, content)
		: realSaveCharacteristicRequirements(projectId, characteristicId, content);
};

export const generateCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGenerateCharacteristicRequirements(projectId, characteristicId)
		: realGenerateCharacteristicRequirements(projectId, characteristicId);
};

export const getCharacteristicRequirements = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGetCharacteristicRequirements(projectId, characteristicId)
		: realGetCharacteristicRequirements(projectId, characteristicId);
};
