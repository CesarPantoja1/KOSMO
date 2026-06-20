import type { AlternativeCharacteristic, Characteristic } from './types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let mockCharacteristics: Characteristic[] = [
	{
		id: '1',
		code: 'C01',
		title: 'Administración de Perfiles y Permisos de Usuario',
		description:
			'Permite crear cuentas para empleados y asignarles roles específicos (Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y funciones sensibles del sistema.',
	},
	{
		id: '2',
		code: 'C02',
		title: 'Gestión de Inventario',
		description:
			'Control de stock, entradas y salidas de productos, alertas de inventario bajo y registro de movimientos con trazabilidad.',
	},
	{
		id: '3',
		code: 'C03',
		title: 'Módulo de Ventas',
		description:
			'Registro de ventas con cálculo automático de impuestos, descuentos y múltiples métodos de pago. Genera facturas electrónicas y tickets.',
	},
	{
		id: '4',
		code: 'C04',
		title: 'Reportes y Dashboard',
		description:
			'Visualización de indicadores clave como ventas diarias, productos más vendidos, márgenes de ganancia y tendencias de consumo.',
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
	await delay(1000);
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
	characteristics: { title: string; description: string }[],
): Promise<Characteristic[]> => {
	await delay(600);
	const newChars: Characteristic[] = characteristics.map((c, i) => ({
		id: String(Date.now() + i),
		code: `C${String(mockCharacteristics.length + i + 1).padStart(2, '0')}`,
		title: c.title,
		description: c.description,
	}));
	mockCharacteristics = [...mockCharacteristics, ...newChars];
	return newChars;
};
