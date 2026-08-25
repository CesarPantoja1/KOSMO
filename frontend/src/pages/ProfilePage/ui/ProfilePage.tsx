'use client';

import { useState } from 'react';
import { useAuthStore } from '@/entities/user';
import { AiConfigTab } from './AiConfigTab';

function ChangePasswordMock() {
	const [currentPassword, setCurrentPassword] = useState('');
	const [newPassword, setNewPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [error, setError] = useState('');
	const [success, setSuccess] = useState('');
	const [loading, setLoading] = useState(false);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		setError('');
		setSuccess('');

		if (newPassword.length < 12) {
			setError('La contraseña debe tener al menos 12 caracteres.');
			return;
		}

		if (newPassword !== confirmPassword) {
			setError('Las contraseñas no coinciden.');
			return;
		}

		setLoading(true);
		setTimeout(() => {
			setLoading(false);
			setSuccess('Contraseña actualizada correctamente.');
			setCurrentPassword('');
			setNewPassword('');
			setConfirmPassword('');
		}, 1500);
	};

	return (
		<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
			<h3 className='text-lg font-semibold text-neutral-800 mb-4'>Cambiar contraseña</h3>
			<form onSubmit={handleSubmit} className='flex flex-col gap-4'>
				{error && (
					<div className='bg-error-50 text-error-700 border border-error-500/20 rounded-lg px-4 py-3 text-sm'>
						{error}
					</div>
				)}
				{success && (
					<div className='bg-success-50 text-success-700 border border-success-500/20 rounded-lg px-4 py-3 text-sm'>
						{success}
					</div>
				)}
				<div>
					<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
						Contraseña actual
					</label>
					<input
						type='password'
						value={currentPassword}
						onChange={(e) => setCurrentPassword(e.target.value)}
						className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all placeholder:text-neutral-400 w-full'
						required
					/>
				</div>
				<div>
					<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
						Nueva contraseña
					</label>
					<input
						type='password'
						value={newPassword}
						onChange={(e) => setNewPassword(e.target.value)}
						minLength={12}
						className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all placeholder:text-neutral-400 w-full'
						required
					/>
				</div>
				<div>
					<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
						Confirmar nueva contraseña
					</label>
					<input
						type='password'
						value={confirmPassword}
						onChange={(e) => setConfirmPassword(e.target.value)}
						minLength={12}
						className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all placeholder:text-neutral-400 w-full'
						required
					/>
				</div>
				<button
					type='submit'
					disabled={loading}
					className='btn btn-primary w-full disabled:opacity-50'
				>
					{loading ? 'Actualizando...' : 'Actualizar contraseña'}
				</button>
			</form>
		</div>
	);
}

function IntegrationsMock() {
	const [connected, setConnected] = useState(false);
	const [loading, setLoading] = useState(false);

	const handleToggle = () => {
		setLoading(true);
		setTimeout(() => {
			setConnected(!connected);
			setLoading(false);
		}, 800);
	};

	return (
		<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
			<h3 className='text-lg font-semibold text-neutral-800 mb-4'>Integraciones</h3>
			<div className='flex items-center justify-between'>
				<div className='flex items-center gap-3'>
					<svg
						className='w-6 h-6 text-neutral-800'
						viewBox='0 0 24 24'
						fill='currentColor'
					>
						<path d='M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z' />
					</svg>
					<div>
						<p className='text-neutral-800 font-medium'>GitHub</p>
						<p className='text-neutral-500 text-sm'>
							{connected ? 'Conectado' : 'No conectado'}
						</p>
					</div>
				</div>
				<button
					type='button'
					onClick={handleToggle}
					disabled={loading}
					className={connected ? 'btn btn-sm btn-destructive' : 'btn btn-primary btn-sm'}
				>
					{loading ? 'Procesando...' : connected ? 'Desconectar' : 'Conectar'}
				</button>
			</div>
		</div>
	);
}

function CuentaTab() {
	const user = useAuthStore((state) => state.user);
	const subject = user?.subject || 'No disponible';
	const scopes = user?.scopes || [];

	return (
		<div className='flex flex-col gap-6 animate-fade-in'>
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
				<h3 className='text-lg font-semibold text-neutral-800 mb-4'>
					Información del usuario
				</h3>
				<div className='flex flex-col gap-4'>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Subject
						</label>
						<p className='text-neutral-800 font-mono text-sm bg-neutral-50 border border-neutral-300 rounded-lg px-3 py-2.5'>
							{subject}
						</p>
					</div>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Scopes
						</label>
						<div className='flex flex-wrap gap-2'>
							{scopes.length > 0 ? (
								scopes.map((scope) => (
									<span
										key={scope}
										className='text-xs font-medium px-2.5 py-1 rounded-full bg-primary-500/10 text-primary-600 border border-primary-500/20'
									>
										{scope}
									</span>
								))
							) : (
								<span className='text-neutral-400 text-sm'>Sin scopes</span>
							)}
						</div>
					</div>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Estado
						</label>
						<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20'>
							Activo
						</span>
					</div>
				</div>
			</div>
			<ChangePasswordMock />
			<IntegrationsMock />
		</div>
	);
}

type TabType = 'cuenta' | 'ia';

function ProfilePage() {
	const [activeTab, setActiveTab] = useState<TabType>('cuenta');

	return (
		<div className='min-h-screen bg-neutral-0 p-6'>
			<div className='max-w-3xl mx-auto'>
				<div className='mb-6'>
					<h1 className='text-2xl font-bold text-neutral-800'>Perfil</h1>
					<p className='text-neutral-500 mt-1'>Gestiona tu cuenta y configuración</p>
				</div>

				<div className='flex gap-1 border-b border-neutral-200 mb-6'>
					<button
						type='button'
						onClick={() => setActiveTab('cuenta')}
						className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
							activeTab === 'cuenta'
								? 'text-primary-500 border-primary-500'
								: 'text-neutral-500 border-transparent hover:text-neutral-700'
						}`}
					>
						Cuenta
					</button>
					<button
						type='button'
						onClick={() => setActiveTab('ia')}
						className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
							activeTab === 'ia'
								? 'text-primary-500 border-primary-500'
								: 'text-neutral-500 border-transparent hover:text-neutral-700'
						}`}
					>
						Inteligencia Artificial
					</button>
				</div>

				{activeTab === 'cuenta' && <CuentaTab />}
				{activeTab === 'ia' && <AiConfigTab />}
			</div>
		</div>
	);
}

export { ProfilePage };
