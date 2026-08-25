'use client';

import { useState, useCallback, useMemo } from 'react';
import { useAiConfigStore } from '../model/ai-config-store';
import {
	AI_PROVIDERS,
	DEFAULT_AI_PROVIDER,
	DEFAULT_AI_MODEL,
	getProviderModels,
	maskApiKey,
	type AIProvider,
	type SaveAIConfigRequest,
} from '../model/ai-config';

interface AiConfigFormProps {
	onSaved?: () => void;
}

export function AiConfigForm({ onSaved }: AiConfigFormProps) {
	const { config, loading, error, testResult, testLoading, testError, saveConfig, testConnection, clearTestResult } =
		useAiConfigStore();

	const [provider, setProvider] = useState<AIProvider>(config?.provider ?? DEFAULT_AI_PROVIDER);
	const [model, setModel] = useState(config?.model ?? DEFAULT_AI_MODEL);
	const [apiKey, setApiKey] = useState('');
	const [showApiKey, setShowApiKey] = useState(false);
	const [isEditing, setIsEditing] = useState(false);

	const availableModels = useMemo(() => getProviderModels(provider), [provider]);

	const handleProviderChange = useCallback(
		(newProvider: AIProvider) => {
			setProvider(newProvider);
			const models = getProviderModels(newProvider);
			if (models.length > 0 && !models.includes(model)) {
				setModel(models[0]);
			}
		},
		[model],
	);

	const handleTestConnection = async () => {
		if (!apiKey && !config?.has_api_key) return;
		await testConnection({
			provider,
			model,
			api_key: apiKey || null,
		});
	};

	const handleSave = async () => {
		const data: SaveAIConfigRequest = {
			provider,
			model,
			api_key: apiKey,
		};
		await saveConfig(data);
		setIsEditing(false);
		setApiKey('');
		setShowApiKey(false);
		clearTestResult();
		onSaved?.();
	};

	const handleCancel = () => {
		setIsEditing(false);
		setApiKey('');
		setShowApiKey(false);
		clearTestResult();
		if (config) {
			setProvider(config.provider);
			setModel(config.model);
		}
	};

	const maskedKey = config?.masked_key ?? maskApiKey(apiKey);
	const hasExistingKey = config?.has_api_key ?? false;
	const canTest = (apiKey || hasExistingKey) && !testLoading;
	const canSave = apiKey && !loading;

	return (
		<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
			<div className='flex items-center justify-between mb-4'>
				<h3 className='text-lg font-semibold text-neutral-800'>Configuración de IA</h3>
				{hasExistingKey && !isEditing && (
					<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20'>
						Configurado
					</span>
				)}
			</div>

			{error && (
				<div className='bg-error-50 text-error-700 border border-error-500/20 rounded-lg px-4 py-3 text-sm mb-4'>
					{error}
				</div>
			)}

			{!isEditing && hasExistingKey && (
				<div className='mb-4'>
					<p className='text-neutral-500 text-sm mb-2'>Clave configurada:</p>
					<p className='text-neutral-800 font-mono text-sm bg-neutral-50 border border-neutral-300 rounded-lg px-3 py-2.5'>
						{maskedKey}
					</p>
				</div>
			)}

			{!isEditing && !hasExistingKey && (
				<p className='text-neutral-400 text-sm mb-4'>No hay clave de API configurada</p>
			)}

			{!isEditing ? (
				<div className='flex gap-2'>
					{hasExistingKey ? (
						<>
							<button type='button' onClick={() => setIsEditing(true)} className='btn btn-secondary btn-sm'>
								Reemplazar
							</button>
							<button
								type='button'
								onClick={async () => {
									const data: SaveAIConfigRequest = {
										provider: DEFAULT_AI_PROVIDER,
										model: DEFAULT_AI_MODEL,
										api_key: '',
									};
									await saveConfig(data);
									onSaved?.();
								}}
								className='btn btn-destructive btn-sm'
							>
								Eliminar
							</button>
						</>
					) : (
						<button type='button' onClick={() => setIsEditing(true)} className='btn btn-primary btn-sm'>
							Agregar API Key
						</button>
					)}
				</div>
			) : (
				<div className='flex flex-col gap-4'>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>Proveedor</label>
						<select
							value={provider}
							onChange={(e) => handleProviderChange(e.target.value as AIProvider)}
							className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all w-full'
						>
							{AI_PROVIDERS.map((p) => (
								<option key={p.value} value={p.value}>
									{p.label}
								</option>
							))}
						</select>
					</div>

					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>Modelo</label>
						<select
							value={model}
							onChange={(e) => setModel(e.target.value)}
							className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all w-full'
						>
							{availableModels.map((m) => (
								<option key={m} value={m}>
									{m}
								</option>
							))}
						</select>
					</div>

					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>Clave de API</label>
						<div className='flex items-center gap-2'>
							<input
								type={showApiKey ? 'text' : 'password'}
								value={apiKey}
								onChange={(e) => setApiKey(e.target.value)}
								placeholder={hasExistingKey ? '••••••••****' : 'sk-...'}
								className='bg-neutral-50 border border-neutral-300 text-neutral-800 rounded-lg px-3 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all placeholder:text-neutral-400 flex-1'
							/>
							<button
								type='button'
								onClick={() => setShowApiKey(!showApiKey)}
								className='px-3 py-2.5 bg-neutral-100 border border-neutral-300 rounded-lg text-neutral-600 hover:text-neutral-800 transition-colors'
							>
								{showApiKey ? 'Ocultar' : 'Mostrar'}
							</button>
						</div>
					</div>

					{testResult && (
						<div
							className={`rounded-lg px-4 py-3 text-sm ${
								testResult.is_connected
									? 'bg-success-50 text-success-700 border border-success-500/20'
									: 'bg-error-50 text-error-700 border border-error-500/20'
							}`}
						>
							<p className='font-medium'>{testResult.message}</p>
							{testResult.is_connected && (
								<p className='text-xs mt-1'>Modelo detectado: {testResult.detected_model}</p>
							)}
						</div>
					)}

					{testError && (
						<div className='bg-error-50 text-error-700 border border-error-500/20 rounded-lg px-4 py-3 text-sm'>
							{testError}
						</div>
					)}

					<div className='flex gap-2'>
						<button
							type='button'
							onClick={handleTestConnection}
							disabled={!canTest}
							className='btn btn-secondary btn-sm disabled:opacity-50'
						>
							{testLoading ? 'Probando...' : 'Probar conexión'}
						</button>
						<button
							type='button'
							onClick={handleSave}
							disabled={!canSave}
							className='btn btn-primary btn-sm disabled:opacity-50'
						>
							{loading ? 'Guardando...' : 'Guardar'}
						</button>
						<button type='button' onClick={handleCancel} className='btn btn-secondary btn-sm'>
							Cancelar
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
