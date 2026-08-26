'use client';

import { Suspense, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/entities/user';
import { RootNavbar } from '@/widgets';
import { Hero } from './Hero';
import { FlowSteps } from './FlowSteps';
import { Features } from './Features';
import { SddSection } from './SddSection';
import { ApiKeySection } from './ApiKeySection';
import { CtaSection } from './CtaSection';
import { AuthModal } from './AuthModal';
import { SessionExpiredWatcher } from './SessionExpiredWatcher';

export function RootPage() {
	const [showAuthModal, setShowAuthModal] = useState(false);
	const [sessionExpired, setSessionExpired] = useState(false);
	const router = useRouter();
	const accessToken = useAuthStore((s) => s.accessToken);

	const handleSessionExpired = () => {
		setSessionExpired(true);
		setShowAuthModal(true);
	};

	const handleComenzar = () => {
		if (accessToken) {
			router.push('/proyecto');
		} else {
			setShowAuthModal(true);
		}
	};

	return (
		<div className='min-h-screen bg-neutral-0 text-neutral-800'>
			<RootNavbar onComenzar={handleComenzar} />
			<Hero onComenzar={handleComenzar} />
			<Features />x
			<FlowSteps />
			<SddSection />
			<ApiKeySection />
			<CtaSection onComenzar={handleComenzar} />
			<AuthModal
				isOpen={showAuthModal}
				onClose={() => setShowAuthModal(false)}
				sessionExpired={sessionExpired && showAuthModal}
			/>
			<Suspense fallback={null}>
				<SessionExpiredWatcher onDetected={handleSessionExpired} />
			</Suspense>
		</div>
	);
}
