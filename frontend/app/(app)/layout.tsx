import { MainNavbar } from '@/widgets/main-navbar/ui/MainNavbar';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	const props = {
		project: { name: 'Proyecto Ejemplo' },
		phases: [
			{ key: 'idea', label: 'Idea' },
			{ key: 'discovery', label: 'Discovery' },
			{ key: 'requirements', label: 'Requirements' },
			{ key: 'modeling', label: 'Modeling' },
		],
		provider: 'OpenAI',
	};

	return (
		<div className='bg-green-500'>
			<MainNavbar {...props} />
			{children}
		</div>
	);
}
