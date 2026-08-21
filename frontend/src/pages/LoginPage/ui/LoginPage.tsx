'use client';

import { useAuthStore, authApi } from '@/entities/user';
import { formatApiError } from '@/shared/api';
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
			await authApi.login(email, password);
			router.push('/proyecto');
		} catch (err) {
			const status = (err as { status?: number }).status;
			if (status === 401) {
				setError('Credenciales inválidas');
			} else {
				setError(formatApiError(err, 'Error al iniciar sesión'));
			}
		} finally {
			setIsLoading(false);
		}
	};

	if (isAuthDisabled) return null;

	return (
		<div className='flex items-center justify-center min-h-screen bg-neutral-900 p-4'>
			<div className='w-full max-w-sm animate-fade-in'>
				<form
					onSubmit={handleSubmit}
					className='bg-neutral-800 p-8 rounded-xl shadow-3 border border-neutral-700'
				>
					<div className='mb-8 text-center'>
						<h1 className='text-3xl font-bold text-primary-500'>KOSMO</h1>
						<p className='text-neutral-400 mt-2'>Iniciar sesión</p>
					</div>

					{error && (
						<div className='bg-error-50 border border-error-500/50 text-error-700 p-3 rounded-lg mb-4 text-sm'>
							{error}
						</div>
					)}

					<div className='flex flex-col gap-4'>
						<div>
							<label className='block text-neutral-300 text-sm font-medium mb-1.5'>
								Correo electrónico
							</label>
							<input
								type='email'
								className='w-full bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500'
								placeholder='tu@email.com'
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								disabled={isLoading}
								autoComplete='email'
							/>
						</div>
						<div>
							<label className='block text-neutral-300 text-sm font-medium mb-1.5'>
								Contraseña
							</label>
							<input
								type='password'
								className='w-full bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500'
								placeholder='Tu contraseña'
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								disabled={isLoading}
								autoComplete='current-password'
							/>
						</div>
						<button
							type='submit'
							disabled={isLoading}
							className='btn btn-primary btn-lg w-full mt-2'
						>
							{isLoading ? 'Iniciando...' : 'Entrar'}
						</button>

						<div className='text-center mt-2'>
							<a
								href='/registro'
								className='text-primary-500 hover:text-primary-600 text-sm font-medium transition-colors'
							>
								¿No tienes cuenta? Regístrate
							</a>
						</div>
					</div>
				</form>
			</div>
		</div>
	);
};

export { LoginPage };
