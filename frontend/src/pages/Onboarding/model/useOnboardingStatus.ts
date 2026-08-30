'use client';

import { useCallback, useEffect, useState } from 'react';
import type { IntegrationStatus } from '@/entities/integration';
import { getIntegrationStatus } from '@/entities/integration';
import { useAiConfigStore } from '@/entities/ai-config';

export interface OnboardingStatus {
	github: IntegrationStatus | null;
	railway: IntegrationStatus | null;
	hasApiKey: boolean;
	loading: boolean;
	refresh: () => Promise<void>;
}

export function useOnboardingStatus(): OnboardingStatus {
	const [github, setGithub] = useState<IntegrationStatus | null>(null);
	const [railway, setRailway] = useState<IntegrationStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const { config, fetchConfig } = useAiConfigStore();

	const refresh = useCallback(async () => {
		setLoading(true);
		try {
			const [gh, rw] = await Promise.all([
				getIntegrationStatus('github'),
				getIntegrationStatus('railway'),
			]);
			setGithub(gh);
			setRailway(rw);
			await fetchConfig();
		} catch {
			// noop
		} finally {
			setLoading(false);
		}
	}, [fetchConfig]);

	useEffect(() => {
		let cancelled = false;

		async function load() {
			try {
				const [gh, rw] = await Promise.all([
					getIntegrationStatus('github'),
					getIntegrationStatus('railway'),
				]);
				if (!cancelled) {
					setGithub(gh);
					setRailway(rw);
				}
				await fetchConfig();
			} catch {
				// noop
			} finally {
				if (!cancelled) setLoading(false);
			}
		}

		void load();
		return () => {
			cancelled = true;
		};
	}, [fetchConfig]);

	return {
		github,
		railway,
		hasApiKey: config?.has_api_key ?? false,
		loading,
		refresh,
	};
}
