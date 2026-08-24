'use client';

import { useState } from 'react';
import { Login } from './Login';
import { Register } from './Register';

interface AuthModalProps {
	isOpen: boolean;
	onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
	const [authView, setAuthView] = useState<'login' | 'register'>('login');

	if (!isOpen) return null;

	return (
		<div
			className='fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm'
			onClick={onClose}
		>
			<div
				className='relative w-full max-w-md mx-4 animate-slide-down'
				onClick={(e) => e.stopPropagation()}
			>
				{authView === 'login' ? (
					<Login
						onClose={onClose}
						onSwitchToRegister={() => setAuthView('register')}
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
