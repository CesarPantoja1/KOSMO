'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getIntegrationStatus } from '@/entities/integration';

export function useIntegrationGate() {
	const router = useRouter();
	const [isReady, setIsReady] = useState(false);
	const [githubConnected, setGithubConnected] = useState(false);

	useEffect(() => {
		let cancelled = false;

		async function check() {
			try {
				const status = await getIntegrationStatus('github');
				if (cancelled) return;

				if (!status.is_connected) {
					router.replace('/onboarding');
					return;
				}

				setGithubConnected(true);
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

	return { isReady, githubConnected };
}
