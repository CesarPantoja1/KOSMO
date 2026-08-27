'use client';

import { useState } from 'react';
import { Login } from './Login';
import { Register } from './Register';

interface AuthModalProps {
	isOpen: boolean;
	onClose: () => void;
	sessionExpired?: boolean;
}

export function AuthModal({ isOpen, onClose, sessionExpired }: AuthModalProps) {
	const [authView, setAuthView] = useState<'login' | 'register'>('login');

	if (!isOpen) return null;

	return (
		<div
			className='fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-xs'
			onClick={onClose}
		>
			<div
				className='relative w-full max-w-md mx-4'
				onClick={(e) => e.stopPropagation()}
			>
				{authView === 'login' ? (
					<Login
						onClose={onClose}
						onSwitchToRegister={() => setAuthView('register')}
						sessionExpired={sessionExpired}
					/>
				) : (
					<Register
						onClose={onClose}
						onSwitchToLogin={() => setAuthView('login')}
					/>
				)}
			</div>
		</div>
	);
}
