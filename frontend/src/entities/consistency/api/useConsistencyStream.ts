'use client';

import { useCallback, useRef, useState } from 'react';
import type React from 'react';

interface PhaseProgress {
	phase: string;
	status: 'evaluating' | 'done' | 'error';
	message: string;
	affectedCount: number;
}

interface ConsistencyStreamState {
	phases: PhaseProgress[];
	isComplete: boolean;
	report: Record<string, unknown> | null;
	error: string | null;
}

interface UseConsistencyStreamOptions {
	projectId: string;
	phaseOrigin: string;
	changes: Array<{ section: string; diff_before: string; diff_after: string }>;
}

const PHASE_LABELS: Record<string, string> = {
	discovery: 'Descubrimiento',
	features: 'Características',
	requirements: 'Requisitos',
	model: 'Modelo',
};

function handleEvent(
	event: Record<string, unknown>,
	setState: React.Dispatch<React.SetStateAction<ConsistencyStreamState>>,
) {
	const eventType = event.type as string;

	if (eventType === 'progress') {
		const phase = (event.phase as string) || '';
		setState((prev) => ({
			...prev,
			phases: [
				...prev.phases.filter((p) => p.phase !== phase),
				{
					phase,
					status: event.status === 'error' ? 'error' : 'evaluating',
					message: (event.message as string) || '',
					affectedCount: 0,
				},
			],
		}));
	} else if (eventType === 'phase_result') {
		const phase = (event.phase as string) || '';
		const affectedCount = (event.affected_count as number) || 0;
		setState((prev) => ({
			...prev,
			phases: [
				...prev.phases.filter((p) => p.phase !== phase),
				{
					phase,
					status: 'done',
					message: (event.message as string) || '',
					affectedCount,
				},
			],
		}));
	} else if (eventType === 'complete') {
		setState((prev) => ({
			...prev,
			isComplete: true,
			report: (event.report as Record<string, unknown>) || null,
		}));
	} else if (eventType === 'error') {
		setState((prev) => ({
			...prev,
			error: (event.message as string) || 'Error desconocido',
			isComplete: true,
		}));
	}
}

export function useConsistencyStream() {
	const [state, setState] = useState<ConsistencyStreamState>({
		phases: [],
		isComplete: false,
		report: null,
		error: null,
	});

	const abortRef = useRef<AbortController | null>(null);

	const start = useCallback(({ projectId, phaseOrigin, changes }: UseConsistencyStreamOptions) => {
		const controller = new AbortController();
		abortRef.current = controller;

		setState({
			phases: [],
			isComplete: false,
			report: null,
			error: null,
		});

		const apiBase = process.env.NEXT_PUBLIC_API_URL?.trim() || 'http://localhost:8000';
		const token = localStorage.getItem('access_token');
		const headers: Record<string, string> = { 'Content-Type': 'application/json' };
		if (token) headers['Authorization'] = `Bearer ${token}`;

		fetch(`${apiBase}/api/v1/projects/${projectId}/consistency/evaluate/stream`, {
			method: 'POST',
			headers,
			body: JSON.stringify({ phase_origin: phaseOrigin, changes }),
			signal: controller.signal,
		})
			.then(async (response) => {
				if (!response.ok || !response.body) {
					const text = await response.text().catch(() => '');
					setState((prev) => ({ ...prev, error: text || 'Error del servidor', isComplete: true }));
					return;
				}

				const reader = response.body.getReader();
				const decoder = new TextDecoder();
				let buffer = '';

				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() || '';

					for (const line of lines) {
						if (!line.startsWith('data: ')) continue;
						const data = line.slice(6);
						try {
							const event = JSON.parse(data);
							handleEvent(event, setState);
						} catch {
							// ignore malformed lines
						}
					}
				}
			})
			.catch((err) => {
				if ((err as Error).name === 'AbortError') return;
				setState((prev) => ({
					...prev,
					error: (err as Error).message || 'Error de conexión',
					isComplete: true,
				}));
			});
	}, []);

	const abort = useCallback(() => {
		abortRef.current?.abort();
	}, []);

	const phaseLabels = PHASE_LABELS;

	return { ...state, start, abort, phaseLabels };
}
