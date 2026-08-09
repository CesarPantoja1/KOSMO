'use client';

import { forwardRef } from 'react';
import { MaxEditor, MinEditor } from '@/feature/markdown-editor/ui/icons';

import type { PlantUmlViewerProps } from '../model/types';
import { useRender } from '../hooks/useRender';
import { usePanZoom } from '../hooks/usePanZoom';
import { ZOOM_MAX, ZOOM_MIN } from '../lib/zoom';

export const PlantUmlViewer = forwardRef<HTMLDivElement, PlantUmlViewerProps>(
	function PlantUmlViewer({ source, isMaximized, onMaximize, onMinimize }, ref) {
		const { svg, state, error } = useRender(source);
		const {
			zoom,
			tx,
			ty,
			isPanning,
			viewportRef,
			zoomIn,
			zoomOut,
			zoomReset,
			handlePanStart,
			handlePanMove,
			handlePanEnd,
		} = usePanZoom(state === 'done');

		if (!source.trim()) {
			return null;
		}

		return (
		<div ref={ref} className='flex-1 min-h-0 overflow-y-auto'>
			<div className='flex items-center justify-between py-2 bg-neutral-100 border-b border-neutral-200 px-3'>
				<h3 className='text-sm font-semibold text-neutral-600'>Diagrama de actividad</h3>
				<div className='flex items-center gap-1'>
					<button
						type='button'
						onClick={zoomOut}
						disabled={zoom <= ZOOM_MIN}
						className='cursor-pointer flex items-center justify-center rounded-md w-7 h-7 text-sm font-bold text-neutral-500 hover:text-neutral-800 hover:bg-neutral-200 transition-colors disabled:opacity-30 disabled:pointer-events-none'
						title='Alejar'
					>
						−
					</button>
					<button
						type='button'
						onClick={zoomReset}
						className='cursor-pointer px-2 h-7 flex items-center justify-center rounded-md text-xs font-medium text-neutral-500 hover:text-neutral-800 hover:bg-neutral-200 transition-colors'
						title='Restablecer zoom'
					>
						{Math.round(zoom * 100)}%
					</button>
					<button
						type='button'
						onClick={zoomIn}
						disabled={zoom >= ZOOM_MAX}
						className='cursor-pointer flex items-center justify-center rounded-md w-7 h-7 text-sm font-bold text-neutral-500 hover:text-neutral-800 hover:bg-neutral-200 transition-colors disabled:opacity-30 disabled:pointer-events-none'
						title='Acercar'
					>
						+
					</button>
					<div className='w-px h-5 bg-neutral-300 mx-1' />
					<button
						type='button'
						className='cursor-pointer size-7 flex items-center justify-center rounded-md text-neutral-500 hover:text-neutral-800 hover:bg-neutral-200 transition-colors'
						onClick={isMaximized ? onMinimize : onMaximize}
						title={isMaximized ? 'Restablecer' : 'Expandir'}
					>
						{isMaximized ? <MinEditor size={20} /> : <MaxEditor size={20} />}
					</button>
				</div>
			</div>

			{(state === 'loading-engine' || state === 'rendering') && (
				<div className='flex items-center gap-2 text-neutral-400 text-sm py-8 justify-center'>
					<svg
						className='animate-spin size-4'
						viewBox='0 0 24 24'
						fill='none'
						aria-hidden='true'
					>
						<circle
							className='opacity-25'
							cx='12'
							cy='12'
							r='10'
							stroke='currentColor'
							strokeWidth='4'
						/>
						<path
							className='opacity-75'
							fill='currentColor'
							d='M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z'
						/>
					</svg>
					<span>
						{state === 'loading-engine'
							? 'Cargando motor de diagramas...'
							: 'Renderizando diagrama...'}
					</span>
				</div>
			)}

			{state === 'error' && (
				<div className='bg-error-50 border border-error-500/30 rounded-lg p-4 m-3 text-error-700 text-sm'>
					<p className='font-medium mb-1'>Error al renderizar el diagrama</p>
					<p className='text-error-500 text-xs font-mono'>{error}</p>
				</div>
			)}

			{state === 'done' && svg && (
				<div
					ref={viewportRef}
					onMouseDown={handlePanStart}
					onMouseMove={handlePanMove}
					onMouseUp={handlePanEnd}
					onMouseLeave={handlePanEnd}
					className={`relative overflow-hidden bg-neutral-0 rounded-lg border border-neutral-200 ${isMaximized ? 'h-full' : ''} ${isPanning ? 'cursor-grabbing select-none' : 'cursor-grab'}`}
				>
					<div
						style={{
							transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
							transformOrigin: '0 0',
						}}
						dangerouslySetInnerHTML={{ __html: svg }}
					/>
				</div>
			)}
		</div>
		);
	},
);
