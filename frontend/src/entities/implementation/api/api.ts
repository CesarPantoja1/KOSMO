import { apiClient } from '@/shared/api';
import { API_BASE_URL, USE_MOCKS } from '@/shared/api/config';
import { parseApiError } from '@/shared/api/errors';
import { authHeaders } from '@/shared/api/headers';
import { consumeSse } from '@/shared/lib';
import type { SseEventHandler } from '@/shared/lib';
import type { ImplementationSummary } from '../model/types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockSummary: ImplementationSummary = {
	featureId: '',
	featureTitle: '',
	featureDisplayId: '',
	status: 'completed',
	metrics: [
		{ value: '5', label: 'Pantallas', icon: 'screens', iconBg: 'bg-ai-50', iconColor: 'text-ai-600' },
		{ value: '3', label: 'Entidades', icon: 'entities', iconBg: 'bg-primary-50', iconColor: 'text-primary-600' },
		{ value: '8', label: 'Reglas', icon: 'rules', iconBg: 'bg-warning-50', iconColor: 'text-warning-600' },
		{ value: '4', label: 'Integraciones', icon: 'integrations', iconBg: 'bg-primary-50', iconColor: 'text-primary-600' },
		{ value: '6', label: 'Validaciones', icon: 'validations', iconBg: 'bg-info-50', iconColor: 'text-info-700' },
		{ value: '12', label: 'Acciones', icon: 'actions', iconBg: 'bg-ai-50', iconColor: 'text-ai-600' },
	],
	technologies: ['Next.js', 'TypeScript', 'Tailwind CSS', 'PostgreSQL', 'Node.js'],
	nextSteps: [
		'Descarga el proyecto generado',
		'Continúa personalizando tu aplicación',
		'Comparte o publica tu aplicación cuando esté lista',
	],
	generatedAt: null,
};

const PROGRESS_MESSAGES: Record<string, string> = {
	session_created: 'Sesión de OpenCode creada',
	plan_progress: 'Planificando la implementación...',
	plan_complete: 'Plan aprobado',
	build_progress: 'Generando código...',
	build_complete: 'Código generado, validando...',
};

export function buildSummary(
	featureId: string,
	featureTitle: string,
	featureDisplayId: string,
	data: Record<string, unknown>,
	timestamp: string,
): ImplementationSummary {
	const files = Array.isArray(data.generated_files) ? data.generated_files.length : 0;
	const edges = typeof data.traceability_edges === 'number' ? data.traceability_edges : 0;
	return {
		featureId,
		featureTitle,
		featureDisplayId,
		status: 'completed',
		metrics: [
			{ value: String(files), label: 'Archivos generados', icon: 'screens', iconBg: 'bg-ai-50', iconColor: 'text-ai-600' },
			{ value: '4/4', label: 'Validaciones en verde', icon: 'validations', iconBg: 'bg-info-50', iconColor: 'text-info-700' },
			{ value: String(edges), label: 'Aristas de trazabilidad', icon: 'integrations', iconBg: 'bg-primary-50', iconColor: 'text-primary-600' },
		],
		technologies: ['Next.js', 'TypeScript', 'Tailwind CSS', 'Drizzle ORM', 'Vitest'],
		nextSteps: [
			'Descarga el proyecto generado',
			'Continúa personalizando tu aplicación',
			'Comparte o publica tu aplicación cuando esté lista',
		],
		generatedAt: timestamp || new Date().toISOString(),
	};
}

export const generateImplementation = async (
	featureId: string,
	featureTitle: string,
	featureDisplayId: string,
	onProgress?: (message: string) => void,
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

	const { implementation_id } = await apiClient<{ implementation_id: string }>(
		'/api/v1/implementations',
		{
			method: 'POST',
			body: JSON.stringify({ feature_id: featureId, max_retries: 3 }),
		},
	);
	onProgress?.('Implementación iniciada');

	const res = await fetch(`${API_BASE_URL}/api/v1/implementations/${implementation_id}/events`, {
		headers: authHeaders(),
		cache: 'no-store',
	});
	if (!res.ok) {
		throw parseApiError(res, await res.json().catch(() => null));
	}

	let done: ImplementationSummary | null = null;
	const onEvent: SseEventHandler = (raw) => {
		const eventType = String(raw.event_type ?? '');
		const data = (raw.data ?? {}) as Record<string, unknown>;
		if (eventType === 'retry') {
			const attempt = String(data.attempt ?? '?');
			const max = String(data.max_retries ?? '?');
			onProgress?.(`Corrigiendo errores de validación (intento ${attempt}/${max})`);
		} else if (eventType === 'done' && data.status === 'implemented') {
			done = buildSummary(
				featureId,
				featureTitle,
				featureDisplayId,
				data,
				String(raw.timestamp ?? new Date().toISOString()),
			);
		} else if (eventType === 'error') {
			throw new Error(
				data.status === 'requires_review'
					? 'La validación falló tras agotar los reintentos. Revisa los errores y reintenta.'
					: 'Ocurrió un error durante la generación.',
			);
		} else {
			const message = PROGRESS_MESSAGES[eventType];
			if (message) onProgress?.(message);
		}
	};
	await consumeSse(res, onEvent);

	if (!done) {
		throw new Error('El flujo de generación terminó sin completarse.');
	}
	return done;
};
