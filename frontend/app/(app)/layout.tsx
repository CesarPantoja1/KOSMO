import { MainNavbar } from '@/widgets/main-navbar/ui/MainNavbar';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	const props = {
		project: { name: 'Ferreteria' },
		phases: [
			{ key: 'descubrimiento', label: 'Descubrimiento' },
			{ key: 'caracteristicas', label: 'Características' },
			{ key: 'requisitos', label: 'Requisitos' },
			{ key: 'modelado', label: 'Modelado' },
			{ key: 'implementacion', label: 'Implementación' },
		],
	};

	return (
		<div className='min-h-screen min-w-full max-h-screen'>
			<MainNavbar {...props}>{children}</MainNavbar>
		</div>
	);
}
