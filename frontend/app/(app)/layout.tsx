'use client';

import ConsistencyPage from '@/pages/project/ConsistencyPage/ui/ConsistencyPage';
import { AuthGuard } from '@/shared/ui/AuthGuard';
import { MainNavbar } from '@/widgets';

export default function AppLayout({ children }: { children: React.ReactNode }) {
	return (
		<AuthGuard>
			<div className='min-h-screen min-w-full max-h-screen relative'>
				<MainNavbar>{children}</MainNavbar>
				<ConsistencyPage />
			</div>
		</AuthGuard>
	);
}
