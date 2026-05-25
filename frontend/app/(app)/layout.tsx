import { MainNavbar } from '@/widgets/main-navbar/ui/MainNavbar';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	const props = {
		project: { name: 'Ferreteria' },
		phases: [
			{ key: 'discovery', label: 'Descubrimiento' },
			{ key: 'characteristics', label: 'Características' },
			{ key: 'requirements', label: 'Requisitos' },
			{ key: 'modeling', label: 'Modelado' },
			{ key: 'prototype', label: 'Prototipo' },
			{ key: 'implementation', label: 'Implementación' },
		],
	};

	return (
		<div className='min-h-screen min-w-full max-h-screen bg-blue-500'>
			<MainNavbar {...props}>{children}</MainNavbar>
		</div>
	);
}
