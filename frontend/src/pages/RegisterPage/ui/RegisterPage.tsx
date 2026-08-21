'use client';

import { useAuthStore, authApi } from '@/entities/user';
import { formatApiError } from '@/shared/api';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const RegisterPage = () => {
	const router = useRouter();
	const { accessToken } = useAuthStore();

	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');

	const [error, setError] = useState('');
	const [success, setSuccess] = useState('');
	const [isLoading, setIsLoading] = useState(false);

	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	useEffect(() => {
		if (isAuthDisabled || accessToken) {
			router.push('/proyecto');
		}
	}, [accessToken, isAuthDisabled, router]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!email || !password || !confirmPassword) {
			setError('Todos los campos son obligatorios');
			return;
		}

		if (password !== confirmPassword) {
			setError('Las contraseñas no coinciden');
			return;
		}

		if (password.length < 12) {
			setError('La contraseña debe tener al menos 12 caracteres');
			return;
		}

		setIsLoading(true);
		setError('');
		setSuccess('');

		try {
			await authApi.register(email, password);
			setSuccess('¡Registro exitoso! Redirigiendo al login...');
			setTimeout(() => {
				router.push('/login');
			}, 2000);
		} catch (err) {
			const status = (err as { status?: number }).status;
			if (status === 409) {
				setError('Este correo ya está registrado');
			} else {
				setError(formatApiError(err, 'Error al registrar usuario'));
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
						<p className='text-neutral-400 mt-2'>Crear cuenta</p>
					</div>

					{error && (
						<div className='bg-error-50 border border-error-500/50 text-error-700 p-3 rounded-lg mb-4 text-sm'>
							{error}
						</div>
					)}

					{success && (
						<div className='bg-success-50 border border-success-500/50 text-success-700 p-3 rounded-lg mb-4 text-sm'>
							{success}
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
								placeholder='Mínimo 12 caracteres'
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								disabled={isLoading}
								autoComplete='new-password'
							/>
						</div>
						<div>
							<label className='block text-neutral-300 text-sm font-medium mb-1.5'>
								Confirmar contraseña
							</label>
							<input
								type='password'
								className='w-full bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500'
								placeholder='Repite tu contraseña'
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								disabled={isLoading}
								autoComplete='new-password'
							/>
						</div>
						<button
							type='submit'
							disabled={isLoading}
							className='btn btn-primary btn-lg w-full mt-2'
						>
							{isLoading ? 'Registrando...' : 'Registrarse'}
						</button>

						<div className='text-center mt-2'>
							<a
								href='/login'
								className='text-primary-500 hover:text-primary-600 text-sm font-medium transition-colors'
							>
								¿Ya tienes cuenta? Inicia sesión
							</a>
						</div>
					</div>
				</form>
			</div>
		</div>
	);
};

export { RegisterPage };
