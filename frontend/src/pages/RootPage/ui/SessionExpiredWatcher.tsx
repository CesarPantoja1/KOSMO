'use client';

import { useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

interface SessionExpiredWatcherProps {
	onDetected: () => void;
}

export function SessionExpiredWatcher({ onDetected }: SessionExpiredWatcherProps) {
	const router = useRouter();
	const searchParams = useSearchParams();
	const hasCheckedExpired = useRef(false);

	const sessionExpired = searchParams?.get('session_expired') === 'true';

	useEffect(() => {
		if (sessionExpired && !hasCheckedExpired.current) {
			hasCheckedExpired.current = true;
			onDetected();
			router.replace('/');
		}
	}, [sessionExpired, router, onDetected]);

	return null;
}
