'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/shared/store/auth.store';

export const AuthGuard = ({ children }: { children: React.ReactNode }) => {
	const router = useRouter();
	const pathname = usePathname();
	const { accessToken, initMockUser } = useAuthStore();
	const [mounted, setMounted] = useState(false);
	
	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	useEffect(() => {
		setMounted(true);
		if (isAuthDisabled) {
			initMockUser();
		}
	}, [isAuthDisabled, initMockUser]);

	useEffect(() => {
		if (!mounted) return;
		
		if (!isAuthDisabled && !accessToken && !pathname.startsWith('/login') && !pathname.startsWith('/register')) {
			// router.push('/login');
		}
	}, [accessToken, pathname, router, isAuthDisabled, mounted]);

	if (!mounted) return null;

	// if (!isAuthDisabled && !accessToken && !pathname.startsWith('/login') && !pathname.startsWith('/register')) {
	// 	return null; // Return nothing while redirecting
	// }

	return <>{children}</>;
};
