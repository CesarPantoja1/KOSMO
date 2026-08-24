'use client';

import { useState } from 'react';
import {
	ResponsiveContainer,
	LineChart,
	Line,
	XAxis,
	YAxis,
	Tooltip,
	CartesianGrid,
} from 'recharts';
import { useAuthStore } from 'docs/user';

interface ProviderKeyCardProps {
	name: string;
	color: string;
}

function ProviderKeyCard({ name, color }: ProviderKeyCardProps) {
	const [token, setToken] = useState('');
	const [isEditing, setIsEditing] = useState(false);
	const [showToken, setShowToken] = useState(false);
	const [saved, setSaved] = useState(false);

	const colorMap: Record<string, string> = {
		ai: 'text-ai-500',
		primary: 'text-primary-500',
		info: 'text-info-500',
		warning: 'text-warning-500',
	};

	const maskedToken = saved && token ? `sk-**********...${token.slice(-4)}` : '';

	const handleSave = () => {
		setSaved(true);
		setIsEditing(false);
	};

	const handleDelete = () => {
		setSaved(false);
		setToken('');
	};

	return (
		<div className='bg-neutral-800 border border-neutral-700 rounded-xl p-6'>
			<div className='flex items-center justify-between mb-4'>
				<div className='flex items-center gap-3'>
					<h3
						className={`text-lg font-semibold ${colorMap[color] || 'text-neutral-100'}`}
					>
						{name}
					</h3>
					{saved ? (
						<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20'>
							Configurado
						</span>
					) : (
						<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-neutral-700 text-neutral-400 border border-neutral-600'>
							No configurado
						</span>
					)}
				</div>
				{saved && !isEditing && (
					<button
						type='button'
						onClick={handleDelete}
						className='text-error-700 hover:text-error-500 transition-colors'
					>
						Eliminar
					</button>
				)}
			</div>

			{!isEditing && saved && (
				<p className='text-neutral-300 font-mono text-sm'>{maskedToken}</p>
			)}

			{!isEditing && !saved && <p className='text-neutral-500 text-sm'>No configurado</p>}

			{!isEditing && !saved && (
				<button
					type='button'
					onClick={() => setIsEditing(true)}
					className='btn btn-primary btn-sm mt-4'
				>
					Agregar API Key
				</button>
			)}

			{isEditing && (
				<div className='flex flex-col gap-3 mt-2'>
					<div className='flex items-center gap-2'>
						<input
							type={showToken ? 'text' : 'password'}
							value={token}
							onChange={(e) => setToken(e.target.value)}
							placeholder='sk-...'
							className='bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500 flex-1'
						/>
						<button
							type='button'
							onClick={() => setShowToken(!showToken)}
							className='px-3 py-2.5 bg-neutral-700 border border-neutral-600 rounded-lg text-neutral-300 hover:text-neutral-100 transition-colors'
						>
							{showToken ? 'Ocultar' : 'Mostrar'}
						</button>
					</div>
					<div className='flex gap-2'>
						<button
							type='button'
							onClick={handleSave}
							disabled={!token}
							className='btn btn-primary btn-sm disabled:opacity-50'
						>
							Guardar
						</button>
						<button
							type='button'
							onClick={() => {
								setIsEditing(false);
								setToken('');
							}}
							className='btn btn-sm bg-neutral-700 border border-neutral-600 text-neutral-300'
						>
							Cancelar
						</button>
					</div>
				</div>
			)}
		</div>
	);
}

const chartData = [
	{ day: 'Lun', google: 12400, openai: 18900, anthropic: 8700, deepseek: 6500 },
	{ day: 'Mar', google: 15600, openai: 22100, anthropic: 11200, deepseek: 8900 },
	{ day: 'Mie', google: 11800, openai: 16400, anthropic: 9800, deepseek: 7200 },
	{ day: 'Jue', google: 19200, openai: 25600, anthropic: 14300, deepseek: 11100 },
	{ day: 'Vie', google: 14500, openai: 20800, anthropic: 10600, deepseek: 8400 },
	{ day: 'Sab', google: 8900, openai: 12300, anthropic: 6200, deepseek: 4800 },
	{ day: 'Dom', google: 6200, openai: 8700, anthropic: 4100, deepseek: 3200 },
];

function ConsumptionChart() {
	return (
		<div className='bg-neutral-800 border border-neutral-700 rounded-xl p-6'>
			<h3 className='text-lg font-semibold text-neutral-100 mb-4'>
				Consumo de tokens (últimos 7 días)
			</h3>
			<div className='h-80'>
				<ResponsiveContainer width='100%' height='100%'>
					<LineChart data={chartData}>
						<CartesianGrid strokeDasharray='3 3' stroke='#404040' />
						<XAxis
							dataKey='day'
							tick={{ fill: '#a3a3a3', fontSize: 12 }}
							axisLine={{ stroke: '#404040' }}
							tickLine={false}
						/>
						<YAxis
							tick={{ fill: '#a3a3a3', fontSize: 12 }}
							axisLine={{ stroke: '#404040' }}
							tickLine={false}
							tickFormatter={(value: number) =>
								value >= 1000 ? `${(value / 1000).toFixed(0)}k` : String(value)
							}
						/>
						<Tooltip
							contentStyle={{
								backgroundColor: '#262626',
								border: '1px solid #404040',
								borderRadius: '8px',
								color: '#e5e5e5',
							}}
							labelStyle={{ color: '#d4d4d4' }}
						/>
						<Line
							type='monotone'
							dataKey='google'
							stroke='#4285F4'
							strokeWidth={2}
							dot={false}
							name='Google'
						/>
						<Line
							type='monotone'
							dataKey='openai'
							stroke='#10a37f'
							strokeWidth={2}
							dot={false}
							name='OpenAI'
						/>
						<Line
							type='monotone'
							dataKey='anthropic'
							stroke='#d97706'
							strokeWidth={2}
							dot={false}
							name='Anthropic'
						/>
						<Line
							type='monotone'
							dataKey='deepseek'
							stroke='#3b82f6'
							strokeWidth={2}
							dot={false}
							name='DeepSeek'
						/>
					</LineChart>
				</ResponsiveContainer>
			</div>
		</div>
	);
}

function TokensTab() {
	return (
		<div className='flex flex-col gap-6 animate-fade-in'>
			<div>
				<h3 className='text-lg font-semibold text-neutral-100 mb-4'>API Keys</h3>
				<div className='flex flex-col gap-4'>
					<ProviderKeyCard name='Google' color='info' />
					<ProviderKeyCard name='OpenAI' color='primary' />
					<ProviderKeyCard name='Anthropic' color='warning' />
					<ProviderKeyCard name='DeepSeek' color='ai' />
				</div>
			</div>
			<div>
				<ConsumptionChart />
			</div>
		</div>
	);
}

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
		<div className='bg-neutral-800 border border-neutral-700 rounded-xl p-6'>
			<h3 className='text-lg font-semibold text-neutral-100 mb-4'>Cambiar contraseña</h3>
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
					<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
						Contraseña actual
					</label>
					<input
						type='password'
						value={currentPassword}
						onChange={(e) => setCurrentPassword(e.target.value)}
						className='bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500 w-full'
						required
					/>
				</div>
				<div>
					<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
						Nueva contraseña
					</label>
					<input
						type='password'
						value={newPassword}
						onChange={(e) => setNewPassword(e.target.value)}
						minLength={12}
						className='bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500 w-full'
						required
					/>
				</div>
				<div>
					<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
						Confirmar nueva contraseña
					</label>
					<input
						type='password'
						value={confirmPassword}
						onChange={(e) => setConfirmPassword(e.target.value)}
						minLength={12}
						className='bg-neutral-900 border border-neutral-600 text-neutral-100 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 transition-colors placeholder:text-neutral-500 w-full'
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
		<div className='bg-neutral-800 border border-neutral-700 rounded-xl p-6'>
			<h3 className='text-lg font-semibold text-neutral-100 mb-4'>Integraciones</h3>
			<div className='flex items-center justify-between'>
				<div className='flex items-center gap-3'>
					<svg
						className='w-6 h-6 text-neutral-100'
						viewBox='0 0 24 24'
						fill='currentColor'
					>
						<path d='M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z' />
					</svg>
					<div>
						<p className='text-neutral-100 font-medium'>GitHub</p>
						<p className='text-neutral-400 text-sm'>
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
			<div className='bg-neutral-800 border border-neutral-700 rounded-xl p-6'>
				<h3 className='text-lg font-semibold text-neutral-100 mb-4'>
					Información del usuario
				</h3>
				<div className='flex flex-col gap-4'>
					<div>
						<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
							Subject
						</label>
						<p className='text-neutral-100 font-mono text-sm bg-neutral-900 border border-neutral-600 rounded-lg px-3 py-2.5'>
							{subject}
						</p>
					</div>
					<div>
						<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
							Scopes
						</label>
						<div className='flex flex-wrap gap-2'>
							{scopes.length > 0 ? (
								scopes.map((scope) => (
									<span
										key={scope}
										className='text-xs font-medium px-2.5 py-1 rounded-full bg-primary-500/10 text-primary-500 border border-primary-500/20'
									>
										{scope}
									</span>
								))
							) : (
								<span className='text-neutral-500 text-sm'>Sin scopes</span>
							)}
						</div>
					</div>
					<div>
						<label className='text-neutral-300 text-sm font-medium mb-1.5 block'>
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

type TabType = 'cuenta' | 'tokens';

function ProfilePage() {
	const [activeTab, setActiveTab] = useState<TabType>('cuenta');

	return (
		<div className='min-h-screen bg-neutral-900 p-6'>
			<div className='max-w-3xl mx-auto'>
				<div className='mb-6'>
					<h1 className='text-2xl font-bold text-neutral-0'>Perfil</h1>
					<p className='text-neutral-400 mt-1'>Gestiona tu cuenta y configuración</p>
				</div>

				<div className='flex gap-1 border-b border-neutral-700 mb-6'>
					<button
						type='button'
						onClick={() => setActiveTab('cuenta')}
						className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
							activeTab === 'cuenta'
								? 'text-primary-500 border-primary-500'
								: 'text-neutral-400 border-transparent hover:text-neutral-200'
						}`}
					>
						Cuenta
					</button>
					<button
						type='button'
						onClick={() => setActiveTab('tokens')}
						className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
							activeTab === 'tokens'
								? 'text-primary-500 border-primary-500'
								: 'text-neutral-400 border-transparent hover:text-neutral-200'
						}`}
					>
						Tokens
					</button>
				</div>

				{activeTab === 'cuenta' && <CuentaTab />}
				{activeTab === 'tokens' && <TokensTab />}
			</div>
		</div>
	);
}

export { ProfilePage };
