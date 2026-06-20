import type { Characteristic, AlternativeCharacteristic } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let mockCharacteristics: Characteristic[] = [
	{
		id: '1',
		code: 'C01',
		title: 'Administración de Perfiles y Permisos de Usuario',
		description:
			'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
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
		code: 'C02',
		title: 'Gestión de Inventario',
		description:
			'Control de stock, entradas y salidas de productos, alertas de inventario bajo y registro de movimientos con trazabilidad.',
		requirements: '',
	},
	{
		id: '3',
		code: 'C03',
		title: 'Módulo de Ventas',
		description:
			'Registro de ventas con cálculo automático de impuestos, descuentos y múltiples métodos de pago. Genera facturas electrónicas y tickets.',
		requirements: '',
	},
	{
		id: '4',
		code: 'C04',
		title: 'Reportes y Dashboard',
		description:
			'Visualización de indicadores clave como ventas diarias, productos más vendidos, márgenes de ganancia y tendencias de consumo.',
		requirements: '',
	},
];

const mockAlternatives: AlternativeCharacteristic[] = [
	{
		id: 'a1',
		title: 'Notificaciones y Alertas',
		description:
			'Sistema de notificaciones push y por correo electrónico para alertar sobre eventos críticos como stock bajo, ventas grandes o vencimiento de productos.',
	},
	{
		id: 'a2',
		title: 'Gestión de Clientes y Proveedores',
		description:
			'Registro y administración de clientes y proveedores con historial de compras, créditos, estados de cuenta y datos de contacto.',
	},
	{
		id: 'a3',
		title: 'Módulo de Caja Diaria',
		description:
			'Apertura y cierre de caja, control de ingresos y egresos, arqueo de caja y conciliación con ventas del día.',
	},
];

export const getCharacteristics = async (
	_projectId: string,
): Promise<Characteristic[]> => {
	await delay(800);
	return [...mockCharacteristics];
};

export const getAlternativeCharacteristics = async (
	_projectId: string,
): Promise<AlternativeCharacteristic[]> => {
	await delay(800);
	return [...mockAlternatives];
};

export const addCharacteristics = async (
	_projectId: string,
	items: { title: string; description: string }[],
): Promise<Characteristic[]> => {
	await delay(600);
	const newChars: Characteristic[] = items.map((item, i) => ({
		id: String(Date.now() + i),
		code: `C${String(mockCharacteristics.length + i + 1).padStart(2, '0')}`,
		title: item.title,
		description: item.description,
		requirements: '',
	}));
	mockCharacteristics = [...mockCharacteristics, ...newChars];
	return newChars;
};

export const saveCharacteristicRequirements = async (
	_projectId: string,
	characteristicId: string,
	content: string,
): Promise<void> => {
	await delay(500);
	const idx = mockCharacteristics.findIndex((c) => c.id === characteristicId);
	if (idx !== -1) {
		mockCharacteristics[idx] = { ...mockCharacteristics[idx], requirements: content };
	}
};

export const generateCharacteristicRequirements = async (
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
