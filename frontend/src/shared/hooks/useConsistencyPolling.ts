'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { getConsistencyStatus } from '@/entities/consistency';
import type { ConsistencyStatusResponse } from '@/entities/consistency';

interface UseConsistencyPollingOptions {
	intervalMs?: number;
	enabled?: boolean;
}

export function useConsistencyPolling(
	projectId: string | null,
	options: UseConsistencyPollingOptions = {},
) {
	const { intervalMs = 10_000, enabled = true } = options;
	const [status, setStatus] = useState<ConsistencyStatusResponse | null>(null);
	const [error, setError] = useState<unknown>(null);
	const inFlightRef = useRef(false);

	const refresh = useCallback(async () => {
		if (!projectId || inFlightRef.current) return;
		inFlightRef.current = true;
		try {
			const data = await getConsistencyStatus(projectId);
			setStatus(data);
			setError(null);
		} catch (err) {
			setError(err);
		} finally {
			inFlightRef.current = false;
		}
	}, [projectId]);

	useEffect(() => {
		if (!enabled || !projectId) return;

		const initial = window.setTimeout(() => void refresh(), 0);

		const isVisible = () => document.visibilityState === 'visible';
		const onFocus = () => {
			if (isVisible()) void refresh();
		};

		const interval = window.setInterval(() => {
			if (isVisible()) void refresh();
		}, intervalMs);

		window.addEventListener('focus', onFocus);
		document.addEventListener('visibilitychange', onFocus);

		return () => {
			window.clearTimeout(initial);
			window.clearInterval(interval);
			window.removeEventListener('focus', onFocus);
			document.removeEventListener('visibilitychange', onFocus);
		};
	}, [enabled, projectId, intervalMs, refresh]);

	const active = enabled && projectId !== null;

	return { status: active ? status : null, error, refresh };
}
