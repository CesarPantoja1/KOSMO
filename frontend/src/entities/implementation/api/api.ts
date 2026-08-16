import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type { ImplementationSummary } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockSummary: ImplementationSummary = {
	featureId: '',
	featureTitle: '',
	featureDisplayId: '',
	status: 'completed',
	metrics: [
		{
			value: '5',
			label: 'Pantallas',
			icon: 'screens',
			iconBg: 'bg-ai-50',
			iconColor: 'text-ai-600',
		},
		{
			value: '3',
			label: 'Entidades',
			icon: 'entities',
			iconBg: 'bg-primary-50',
			iconColor: 'text-primary-600',
		},
		{
			value: '8',
			label: 'Reglas',
			icon: 'rules',
			iconBg: 'bg-warning-50',
			iconColor: 'text-warning-600',
		},
		{
			value: '4',
			label: 'Integraciones',
			icon: 'integrations',
			iconBg: 'bg-primary-50',
			iconColor: 'text-primary-600',
		},
		{
			value: '6',
			label: 'Validaciones',
			icon: 'validations',
			iconBg: 'bg-info-50',
			iconColor: 'text-info-700',
		},
		{
			value: '12',
			label: 'Acciones',
			icon: 'actions',
			iconBg: 'bg-ai-50',
			iconColor: 'text-ai-600',
		},
	],
	technologies: ['Next.js', 'TypeScript', 'Tailwind CSS', 'PostgreSQL', 'Node.js'],
	nextSteps: [
		'Descarga el proyecto generado',
		'Continúa personalizando tu aplicación',
		'Comparte o publica tu aplicación cuando esté lista',
	],
	generatedAt: null,
};

export const generateImplementation = async (
	featureId: string,
	featureTitle: string,
	featureDisplayId: string,
): Promise<ImplementationSummary> => {
	if (USE_MOCKS) {
		await delay(2000);
		return {
			...mockSummary,
			featureId,
			featureTitle,
			featureDisplayId,
			generatedAt: new Date().toISOString(),
		};
	}

	return apiClient<ImplementationSummary>(`/api/v1/implementation/generate`, {
		method: 'POST',
		body: JSON.stringify({ feature_id: featureId }),
	});
};

export const getImplementationSummary = async (
	featureId: string,
): Promise<ImplementationSummary | null> => {
	if (USE_MOCKS) {
		await delay(300);
		if (mockSummary.featureId !== featureId) return null;
		return { ...mockSummary, featureId };
	}

	return apiClient<ImplementationSummary>(
		`/api/v1/implementation/${featureId}/summary`,
	);
};
