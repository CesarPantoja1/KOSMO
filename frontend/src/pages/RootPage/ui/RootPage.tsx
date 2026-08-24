'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/entities/user';
import { Navbar } from './Navbar';
import { Hero } from './Hero';
import { FlowSteps } from './FlowSteps';
import { Features } from './Features';
import { SddSection } from './SddSection';
import { ApiKeySection } from './ApiKeySection';
import { CtaSection } from './CtaSection';
import { AuthModal } from './AuthModal';

export function RootPage() {
	const [showAuthModal, setShowAuthModal] = useState(false);
	const router = useRouter();
	const searchParams = useSearchParams();
	const accessToken = useAuthStore((s) => s.accessToken);
	const hasCheckedExpired = useRef(false);

	const sessionExpired = searchParams?.get('session_expired') === 'true';

	useEffect(() => {
		if (sessionExpired && !hasCheckedExpired.current) {
			hasCheckedExpired.current = true;
			setShowAuthModal(true);
			router.replace('/');
		}
	}, [sessionExpired, router]);

	const handleComenzar = () => {
		if (accessToken) {
			router.push('/proyecto');
		} else {
			setShowAuthModal(true);
		}
	};

	return (
		<div className='min-h-screen bg-neutral-0 text-neutral-800'>
			<Navbar onComenzar={handleComenzar} />
			<Hero onComenzar={handleComenzar} />
			<Features />
			<FlowSteps />
			<SddSection />
			<ApiKeySection />
			<CtaSection onComenzar={handleComenzar} />
			<AuthModal
				isOpen={showAuthModal}
				onClose={() => setShowAuthModal(false)}
				sessionExpired={sessionExpired && showAuthModal}
			/>
		</div>
	);
}
