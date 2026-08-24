'use client';

import { useAuthStore, authApi } from 'docs/user';
import { formatApiError } from '@/shared/api';
import { Close } from '@/shared/ui';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface LoginModalProps {
	onClose: () => void;
	onSwitchToRegister: () => void;
	sessionExpired?: boolean;
}

const Login = ({ onClose, onSwitchToRegister, sessionExpired }: LoginModalProps) => {
	const { accessToken } = useAuthStore();
	const router = useRouter();

	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [retryAfter, setRetryAfter] = useState(0);

	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';

	useEffect(() => {
		if (isAuthDisabled || accessToken) {
			onClose();
		}
	}, [accessToken, isAuthDisabled, onClose]);

	useEffect(() => {
		if (retryAfter <= 0) return;
		const timer = setInterval(() => {
			setRetryAfter((prev) => {
				if (prev <= 1) {
					clearInterval(timer);
					setError('');
					return 0;
				}
				return prev - 1;
			});
		}, 1000);
		return () => clearInterval(timer);
	}, [retryAfter]);

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
			onClose();
		} catch (err) {
			const status = (err as { status?: number }).status;
			if (status === 401) {
				setError('Credenciales inválidas');
			} else if (status === 429) {
				const retryAfterValue = (err as { retryAfter?: number }).retryAfter ?? 300;
				setRetryAfter(retryAfterValue);
				setError(`Cuenta bloqueada. Intente de nuevo en ${retryAfterValue} segundos.`);
			} else {
				setError(formatApiError(err, 'Error al iniciar sesión'));
			}
		} finally {
			setIsLoading(false);
		}
	};

	if (isAuthDisabled) return null;

	return (
		<form
			onSubmit={handleSubmit}
			className='bg-neutral-0 p-8 rounded-xl shadow-lg border border-neutral-200'
		>
			<div className='flex items-center justify-between mb-8'>
				<div className='text-center flex-1'>
					<h1 className='text-3xl font-bold text-ai-500'>KOSMO</h1>
					<p className='text-neutral-500 mt-2'>Iniciar sesión</p>
				</div>
				<button
					type='button'
					onClick={onClose}
					className='text-neutral-400 hover:text-neutral-600 transition-colors'
				>
					<Close size={20} color='text-current' />
				</button>
			</div>

			{sessionExpired && (
				<div className='bg-warning-50 border border-warning-500/50 text-warning-700 p-3 rounded-lg mb-4 text-sm'>
					Tu sesión ha expirado. Por favor, inicia sesión nuevamente.
				</div>
			)}

			{error && (
				<div className='bg-error-50 border border-error-500/50 text-error-700 p-3 rounded-lg mb-4 text-sm'>
					{error}
				</div>
			)}

			<div className='flex flex-col gap-4'>
				<div>
					<label className='block text-neutral-600 text-sm font-medium mb-1.5'>
						Correo electrónico
					</label>
					<input
						type='email'
						className='w-full bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-ai-500 transition-colors placeholder:text-neutral-400'
						placeholder='tu@email.com'
						value={email}
						onChange={(e) => setEmail(e.target.value)}
						disabled={isLoading}
						autoComplete='email'
					/>
				</div>
				<div>
					<label className='block text-neutral-600 text-sm font-medium mb-1.5'>
						Contraseña
					</label>
					<input
						type='password'
						className='w-full bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-ai-500 transition-colors placeholder:text-neutral-400'
						placeholder='Tu contraseña'
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						disabled={isLoading}
						autoComplete='current-password'
					/>
				</div>
				<button
					type='submit'
					disabled={isLoading || retryAfter > 0}
					className='btn btn-ai btn-lg w-full mt-2'
				>
					{isLoading
						? 'Iniciando...'
						: retryAfter > 0
							? `Espera ${retryAfter}s`
							: 'Entrar'}
				</button>

				<div className='text-center mt-2'>
					<button
						type='button'
						onClick={onSwitchToRegister}
						className='text-ai-500 hover:text-ai-600 text-sm font-medium transition-colors'
					>
						¿No tienes cuenta? Regístrate
					</button>
				</div>
			</div>
		</form>
	);
};

export { Login };
