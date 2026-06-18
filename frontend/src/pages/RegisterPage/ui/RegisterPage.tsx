'use client';

import { useAuthStore } from '@/shared/store/auth.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
const RegisterPage = () => {
	const router = useRouter();
	const { accessToken } = useAuthStore();
	
	const [name, setName] = useState('');
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
		if (!name || !email || !password || !confirmPassword) {
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
			await new Promise(r => setTimeout(r, 1000));
			setSuccess('¡Registro exitoso! Redirigiendo al login...');
			setTimeout(() => {
				router.push('/login');
			}, 2000);
		} catch (err: any) {
			console.error('Error al registrar:', err);
			setError(err.message || 'Error al registrar usuario');
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
					<p className='text-base-300 mt-2'>Crear cuenta</p>
				</div>
				
				{error && (
					<div className='bg-red-500/10 border border-red-500/50 text-red-500 p-3 rounded mb-4 text-sm'>
						{error}
					</div>
				)}

				{success && (
					<div className='bg-green-500/10 border border-green-500/50 text-green-500 p-3 rounded mb-4 text-sm'>
						{success}
					</div>
				)}

				<div className='flex flex-col gap-4'>
					<div>
						<label className='block text-base-300 text-sm mb-1'>Nombre</label>
						<input 
							type='text' 
							className='w-full bg-base-800 border border-base-700 text-base-100 rounded px-3 py-2 outline-none focus:border-primary-500 transition-colors'
							value={name}
							onChange={(e) => setName(e.target.value)}
							disabled={isLoading}
						/>
					</div>
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
						<label className='block text-base-300 text-sm mb-1'>Contraseña (mínimo 12 caracteres)</label>
						<input 
							type='password' 
							className='w-full bg-base-800 border border-base-700 text-base-100 rounded px-3 py-2 outline-none focus:border-primary-500 transition-colors'
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							disabled={isLoading}
						/>
					</div>
					<div>
						<label className='block text-base-300 text-sm mb-1'>Confirmar contraseña</label>
						<input 
							type='password' 
							className='w-full bg-base-800 border border-base-700 text-base-100 rounded px-3 py-2 outline-none focus:border-primary-500 transition-colors'
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
							disabled={isLoading}
						/>
					</div>
					<button 
						type='submit' 
						disabled={isLoading}
						className='w-full bg-primary-400 hover:bg-primary-500 text-base-950 font-semibold py-2 px-4 rounded mt-2 transition-colors disabled:opacity-50'
					>
						{isLoading ? 'Registrando...' : 'Registrarse'}
					</button>

					<div className='text-center mt-4'>
						<a href='/login' className='text-primary-300 hover:text-primary-200 text-sm'>
							¿Ya tienes cuenta? Inicia sesión
						</a>
					</div>
				</div>
			</form>
		</div>
	);
};

export { RegisterPage };
