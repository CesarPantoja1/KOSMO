'use client';
import { useState } from 'react';

interface PendingItem {
	id: number;
	title: string;
}

const initialItems: PendingItem[] = [
	{ id: 1, title: 'Actualizar Descubrimiento' },
	{ id: 2, title: 'Modificar Características' },
	{ id: 3, title: 'Regenerar Requisitos' },
];

export function FloatingDiscoveryPlan() {
	const [open, setOpen] = useState(false);
	const [items, setItems] = useState(initialItems);

	const removeItem = (id: number) => {
		setItems((prev) => prev.filter((e) => e.id !== id));
	};

	return (
		<div className='fixed bottom-6 left-1/2 z-50 -translate-x-1/2'>
			{/* Lista */}
			{open && (
				<div className='absolute bottom-16 left-0 w-80 overflow-hidden rounded-xl border border-base-800 bg-base-950 shadow-2xl'>
					<div className='border-b border-status-warning/20 bg-status-warning/10 px-4 py-3 text-sm font-semibold text-status-warning'>
						Cambios pendientes
					</div>

					<div className='max-h-72 overflow-y-auto'>
						{items.length === 0 ? (
							<div className='px-4 py-6 text-center text-sm text-base-600'>
								No existen cambios pendientes.
							</div>
						) : (
							items.map((item) => (
								<div
									key={item.id}
									className='flex items-center justify-between border-b border-base-800 px-4 py-3 hover:bg-base-800/20 transition-colors'
								>
									<span className='text-sm text-base-50'>{item.title}</span>

									<button
										onClick={() => removeItem(item.id)}
										className='flex h-6 w-6 items-center justify-center rounded text-base-600 hover:bg-status-error/20 hover:text-status-error'
									>
										✕
									</button>
								</div>
							))
						)}
					</div>
				</div>
			)}
			{/* Botón flotante */}
			<div className='flex overflow-hidden rounded-full border border-status-warning bg-status-warning shadow-xl'>
				{/* Expandir */}
				<button
					onClick={() => setOpen((v) => !v)}
					className='flex h-14 w-14 items-center justify-center border-r border-white/20 text-lg text-base-50 transition hover:bg-white/10'
				>
					<span
						className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
					>
						▲
					</span>
				</button>

				{/* Contenido */}
				<div className='flex items-center gap-3 px-5'>
					<div className='text-xs text-base-50/70'>Plan</div>

					<div className='font-medium text-base-50'>{items.length} cambios pendientes</div>
				</div>
			</div>
		</div>
	);
}
