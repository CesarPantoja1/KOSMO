import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';

import type { ModelingUmlResponse } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockDiagram = `@startuml
!theme plain
skinparam backgroundColor transparent

title BPMN - Venta de Productos

|Cliente|
start
:Solicitar productos;

|Cajero|
:Registrar venta;

|Sistema|
:Consultar inventario;

if (Stock disponible?) then (Sí)

    :Emitir factura;
    :Calcular total;

    |Cliente|
    :Pagar;

    |Sistema|
    :Confirmar pago;
    :Actualizar stock;

    |Cajero|
    :Entregar productos;

    stop

else (No)

    :Mostrar mensaje\\n"Sin stock";

    |Cajero|
    :Informar al cliente;

    stop

endif

@enduml`;

const mockGeneratePlantUmlDiagram = async (
	_projectId: string,
	_characteristicId: string,
): Promise<string> => {
	await delay(600);
	return mockDiagram;
};

const realGeneratePlantUmlDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	const data = await apiClient<ModelingUmlResponse>(
		`/api/v1/features/${characteristicId}/diagram/generate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ project_id: projectId }),
		},
	);
	return data.plantuml_source;
};

const mockGetDiagram = async (
	_projectId: string,
	_characteristicId: string,
): Promise<string> => {
	await delay(600);
	return mockDiagram;
};

const realGetDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	const data = await apiClient<ModelingUmlResponse>(
		`/api/v1/features/${characteristicId}/diagram`,
		{
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		},
	);
	return data.plantuml_source;
};

const isUsingMocks = () => USE_MOCKS;

export const generatePlantUmlDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGeneratePlantUmlDiagram(projectId, characteristicId)
		: realGeneratePlantUmlDiagram(projectId, characteristicId);
};

export const getDiagram = async (
	projectId: string,
	characteristicId: string,
): Promise<string> => {
	return isUsingMocks()
		? mockGetDiagram(projectId, characteristicId)
		: realGetDiagram(projectId, characteristicId);
};


