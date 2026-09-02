'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProjectDeployStatusResponse, DeployRailwayRequest } from './types';
import { getDeployStatus, startDeployRailway } from '../api/api';
import { formatApiError } from '@/shared/api';

const POLL_INTERVAL_MS = 5_000;
const TERMINAL_STATUSES = new Set(['ready', 'failed', 'idle']);

export interface UseDeployStatusReturn {
	status: ProjectDeployStatusResponse | null;
	loading: boolean;
	deploying: boolean;
	error: string | null;
	deploy: (body?: DeployRailwayRequest) => Promise<void>;
	refresh: () => Promise<void>;
}

export function useDeployStatus(projectId: string | null): UseDeployStatusReturn {
	const [status, setStatus] = useState<ProjectDeployStatusResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [deploying, setDeploying] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const mountedRef = useRef(true);

	const fetchStatus = useCallback(async () => {
		if (!projectId) return;
		try {
			const data = await getDeployStatus(projectId);
			if (mountedRef.current) {
				setStatus(data);
				setError(null);
			}
		} catch (err) {
			if (mountedRef.current) {
				setError(formatApiError(err, 'No se pudo obtener el estado del despliegue'));
			}
		} finally {
			if (mountedRef.current) setLoading(false);
		}
	}, [projectId]);

	useEffect(() => {
		mountedRef.current = true;
		let cancelled = false;

		async function init() {
			if (!projectId) return;
			try {
				const data = await getDeployStatus(projectId);
				if (!cancelled && mountedRef.current) {
					setStatus(data);
					setError(null);
				}
			} catch (err) {
				if (!cancelled && mountedRef.current) {
					setError(formatApiError(err, 'No se pudo obtener el estado del despliegue'));
				}
			} finally {
				if (!cancelled && mountedRef.current) setLoading(false);
			}
		}

		init();

		return () => {
			cancelled = true;
			mountedRef.current = false;
			if (timerRef.current) clearTimeout(timerRef.current);
		};
	}, [projectId]);

	useEffect(() => {
		if (!status || TERMINAL_STATUSES.has(status.status)) {
			if (timerRef.current) clearTimeout(timerRef.current);
			return;
		}
		timerRef.current = setTimeout(() => {
			fetchStatus();
		}, POLL_INTERVAL_MS);
		return () => {
			if (timerRef.current) clearTimeout(timerRef.current);
		};
	}, [status, fetchStatus]);

	const deploy = useCallback(
		async (body?: DeployRailwayRequest) => {
			if (!projectId) return;
			setDeploying(true);
			setError(null);
			try {
				const data = await startDeployRailway(projectId, body);
				if (mountedRef.current) {
					setStatus(data);
				}
			} catch (err) {
				if (mountedRef.current) {
					setError(formatApiError(err, 'No se pudo iniciar el despliegue'));
				}
			} finally {
				if (mountedRef.current) setDeploying(false);
			}
		},
		[projectId],
	);

	const refresh = useCallback(async () => {
		setLoading(true);
		await fetchStatus();
	}, [fetchStatus]);

	return { status, loading, deploying, error, deploy, refresh };
}
