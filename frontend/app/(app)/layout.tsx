'use client';

import { MainNavbar } from '@/widgets/main-navbar/ui/MainNavbar';
import { AuthGuard } from '@/shared/ui/AuthGuard';
import { useAppStore } from '@/shared/store/app.store';

export default function AppLayout({ children }: { children: React.ReactNode }) {
	const { currentProject } = useAppStore();

	const props = {
		project: currentProject || { name: 'Sin Proyecto' },
		phases: [
			{ key: 'descubrimiento', label: 'Descubrimiento' },
			{ key: 'caracteristicas', label: 'Características' },
			{ key: 'requisitos', label: 'Requisitos' },
			{ key: 'modelado', label: 'Modelado' },
			{ key: 'implementacion', label: 'Implementación' },
		],
	};

	return (
		<AuthGuard>
			<div className='min-h-screen min-w-full max-h-screen'>
				<MainNavbar {...props}>{children}</MainNavbar>
			</div>
		</AuthGuard>
	);
}
