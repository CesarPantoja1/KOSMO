'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getIntegrationStatus } from '@/entities/integration';

export function useIntegrationGate() {
	const router = useRouter();
	const [isReady, setIsReady] = useState(false);
	const [githubConnected, setGithubConnected] = useState(false);
	const [railwayConnected, setRailwayConnected] = useState(false);

	useEffect(() => {
		let cancelled = false;

		async function check() {
			try {
				const [github, railway] = await Promise.all([
					getIntegrationStatus('github'),
					getIntegrationStatus('railway'),
				]);
				if (cancelled) return;

				if (!github.is_connected || !railway.is_connected) {
					router.replace('/onboarding');
					return;
				}

				setGithubConnected(true);
				setRailwayConnected(true);
				setIsReady(true);
			} catch {
				if (!cancelled) {
					router.replace('/onboarding');
				}
			}
		}

		void check();
		return () => {
			cancelled = true;
		};
	}, [router]);

	return { isReady, githubConnected, railwayConnected };
}
