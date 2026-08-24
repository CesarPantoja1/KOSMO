'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/entities/user';
import { Logo } from '@/shared/ui';

interface NavbarProps {
	onComenzar: () => void;
}

export function Navbar({ onComenzar }: NavbarProps) {
	const router = useRouter();
	const accessToken = useAuthStore((s) => s.accessToken);

	return (
		<header className='sticky top-0 z-50 border-b border-neutral-200 bg-neutral-0/90 backdrop-blur-xl'>
			<div className='mx-auto flex h-20 max-w-7xl items-center justify-between px-6'>
				<div className='flex items-center gap-3'>
					<button
						onClick={() => router.push(accessToken ? '/proyecto' : '/')}
						className='flex items-center gap-3'
					>
						<Logo size={36} />
						<span className='text-xl font-bold tracking-tight text-neutral-800'>
							KOSMO
						</span>
					</button>
				</div>

				<nav className='hidden items-center gap-8 text-sm text-neutral-500 md:flex'>
					<a href='#caracteristicas' className='transition hover:text-neutral-800'>
						Características
					</a>
					<a href='#como-funciona' className='transition hover:text-neutral-800'>
						Cómo funciona
					</a>
					<a href='#metodologia' className='transition hover:text-neutral-800'>
						Metodología
					</a>
				</nav>

				<button onClick={onComenzar} className='btn btn-ai btn-sm'>
					Comenzar
				</button>
			</div>
		</header>
	);
}
