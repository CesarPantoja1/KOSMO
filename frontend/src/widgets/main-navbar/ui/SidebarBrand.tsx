import { useRouter } from 'next/navigation';

import { Logo, Sidebar } from '@/shared/ui';

interface SidebarBrandProps {
	isSidebarExpanded: boolean;
	onToggle: () => void;
}

export function SidebarBrand({ isSidebarExpanded, onToggle }: SidebarBrandProps) {
	const router = useRouter();

	return (
		<div className='relative group flex min-h-16 items-center justify-center border-b border-neutral-700'>
			{isSidebarExpanded ? (
				<>
					<button
						className='text-xl font-bold text-neutral-0 cursor-pointer whitespace-nowrap tracking-widest'
						onClick={() => router.push('/')}
					>
						KOSMO
					</button>
					<button
						className='absolute top-0 bottom-0 right-3 flex items-center justify-center cursor-pointer text-neutral-400 hover:text-neutral-0 transition-colors'
						onClick={onToggle}
					>
						<Sidebar size={22} color='text-current' />
					</button>
				</>
			) : (
				<>
					<span className='select-none group-hover:invisible'>
						<Logo size={28} />
					</span>
					<button
						className='absolute top-0 bottom-0 flex items-center justify-center cursor-pointer text-neutral-400 hover:text-neutral-0 transition-colors opacity-0 group-hover:opacity-100'
						onClick={onToggle}
					>
						<Sidebar size={22} color='text-current' />
					</button>
				</>
			)}
		</div>
	);
}
