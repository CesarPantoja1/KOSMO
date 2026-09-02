'use client';

import type { PreconditionState } from '@/entities/deploy';
import {
	GitHub,
	InfoCircleIcon,
	Load,
	Railway,
	WarningIcon,
} from '@/shared/ui';
import Link from 'next/link';

const DeployPreconditionPanel = ({
	precondition,
	onDeploy,
	deploying,
}: {
	precondition: PreconditionState;
	onDeploy: () => void;
	deploying: boolean;
}) => {
	if (precondition === 'loading') {
		return (
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6 w-full'>
				<div className='flex items-center gap-3 py-4 text-neutral-500 text-sm'>
					<Load size={18} />
					Verificando condiciones de despliegue...
				</div>
			</div>
		);
	}

	if (precondition === 'github-not-linked') {
		return (
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6 w-full'>
				<div className='flex items-center gap-2 mb-3'>
					<div className='flex h-8 w-8 items-center justify-center rounded-md bg-neutral-100'>
						<GitHub size={18} color='text-neutral-800' />
					</div>
					<h3 className='text-lg font-semibold text-neutral-800'>Desplegar en la nube</h3>
				</div>
				<div className='flex items-start gap-3 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3'>
					<WarningIcon size={20} color='text-warning-600' />
					<div className='flex flex-col gap-1'>
						<p className='text-sm font-semibold text-warning-700'>
							Repositorio no vinculado
						</p>
						<p className='text-sm text-warning-700/80'>
							Necesitas conectar tu cuenta de GitHub y sincronizar el código antes de
							publicar.
						</p>
					</div>
				</div>
			</div>
		);
	}

	if (precondition === 'github-not-synced') {
		return (
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6 w-full'>
				<div className='flex items-center gap-2 mb-3'>
					<div className='flex h-8 w-8 items-center justify-center rounded-md bg-neutral-100'>
						<GitHub size={18} color='text-neutral-800' />
					</div>
					<h3 className='text-lg font-semibold text-neutral-800'>Desplegar en la nube</h3>
				</div>
				<div className='flex items-start gap-3 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3'>
					<WarningIcon size={20} color='text-warning-600' />
					<div className='flex flex-col gap-1'>
						<p className='text-sm font-semibold text-warning-700'>
							Sincroniza tu código primero
						</p>
						<p className='text-sm text-warning-700/80'>
							El repositorio en GitHub aún no tiene código sincronizado. Sube tu código
							antes de desplegar.
						</p>
					</div>
				</div>
			</div>
		);
	}

	if (precondition === 'railway-not-linked') {
		return (
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6 w-full'>
				<div className='flex items-center gap-2 mb-3'>
					<div className='flex h-8 w-8 items-center justify-center rounded-md bg-railway-50'>
						<Railway size={18} color='text-railway-700' />
					</div>
					<h3 className='text-lg font-semibold text-neutral-800'>Desplegar en la nube</h3>
				</div>
				<div className='flex flex-col gap-3'>
					<div className='flex items-start gap-3 rounded-lg border border-info-200 bg-info-50 px-4 py-3'>
						<InfoCircleIcon size={20} color='text-info-600' />
						<div className='flex flex-col gap-1'>
							<p className='text-sm font-semibold text-info-700'>
								Vincula tu cuenta de Railway
							</p>
							<p className='text-sm text-info-700/80'>
								Conecta tu cuenta de Railway para publicar tu aplicación en la nube.
							</p>
						</div>
					</div>
					<Link href='/perfil' className='btn btn-primary btn-sm self-start'>
						Conectar Railway
					</Link>
				</div>
			</div>
		);
	}

	return (
		<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6 w-full'>
			<div className='flex items-center gap-2 mb-4'>
				<div className='flex h-8 w-8 items-center justify-center rounded-md bg-railway-50'>
					<Railway size={18} color='text-railway-700' />
				</div>
				<h3 className='text-lg font-semibold text-neutral-800'>Desplegar en la nube</h3>
			</div>
			<p className='text-sm text-neutral-500 mb-4'>
				Publica tu aplicación en Railway con un clic. Se creará un servicio con tu código
				sincronizado.
			</p>
			<button
				type='button'
				onClick={onDeploy}
				disabled={deploying}
				className='btn btn-primary btn-sm'
			>
				{deploying ? (
					<>
						<Load size={16} />
						Iniciando despliegue...
					</>
				) : (
					<>
						<Railway size={16} />
						Desplegar en Railway
					</>
				)}
			</button>
		</div>
	);
};

export { DeployPreconditionPanel };
