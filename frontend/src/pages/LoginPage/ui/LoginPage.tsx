'use client';

import { useAuthStore } from '@/shared/store/auth.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const LoginPage = () => {
	const router = useRouter();
	const { accessToken } = useAuthStore();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [isLoading, setIsLoading] = useState(false);

	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	useEffect(() => {
		if (isAuthDisabled || accessToken) {
			router.push('/proyecto');
		}
	}, [accessToken, isAuthDisabled, router]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!email || !password) {
			setError('Todos los campos son obligatorios');
			return;
		}

		setIsLoading(true);
		setError('');

		try {
			// Simulación
			await new Promise(r => setTimeout(r, 1000));
			router.push('/proyecto');
		} catch (err) {
			const errorMsg = err instanceof Error ? err.message : 'Error al iniciar sesión';
			console.error('Error al iniciar sesión:', err);
			setError(errorMsg);
		} finally {
			setIsLoading(false);
		}
	};

	if (isAuthDisabled) return null;

	return (
		<div className='flex items-center justify-center min-h-screen bg-base-950 p-4'>
			<form onSubmit={handleSubmit} className='bg-base-900 p-8 rounded-lg shadow-xl max-w-sm w-full border border-base-800'>
				<div className='mb-8 text-center'>
					<h1 className='text-3xl font-bold text-primary-300'>KOSMO</h1>
					<p className='text-base-300 mt-2'>Iniciar sesión</p>
				</div>
				
				{error && (
					<div className='bg-red-500/10 border border-red-500/50 text-red-500 p-3 rounded mb-4 text-sm'>
						{error}
					</div>
				)}

				<div className='flex flex-col gap-4'>
					<div>
						<label className='block text-base-300 text-sm mb-1'>Correo electrónico</label>
						<input 
							type='email' 
							className='w-full bg-base-800 border border-base-700 text-base-100 rounded px-3 py-2 outline-none focus:border-primary-500 transition-colors'
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							disabled={isLoading}
						/>
					</div>
					<div>
						<label className='block text-base-300 text-sm mb-1'>Contraseña</label>
						<input 
							type='password' 
							className='w-full bg-base-800 border border-base-700 text-base-100 rounded px-3 py-2 outline-none focus:border-primary-500 transition-colors'
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							disabled={isLoading}
						/>
					</div>
					<button 
						type='submit' 
						disabled={isLoading}
						className='w-full bg-primary-400 hover:bg-primary-500 text-base-950 font-semibold py-2 px-4 rounded mt-2 transition-colors disabled:opacity-50'
					>
						{isLoading ? 'Iniciando...' : 'Entrar'}
					</button>

					<div className='text-center mt-4'>
						<a href='/register' className='text-primary-300 hover:text-primary-200 text-sm'>
							¿No tienes cuenta? Regístrate
						</a>
					</div>
				</div>
			</form>
		</div>
	);
};

export { LoginPage };
