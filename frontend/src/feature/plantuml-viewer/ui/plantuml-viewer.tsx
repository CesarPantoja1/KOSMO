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
				<div className='flex items-center justify-between py-1.5 bg-base-100 rounded-sm px-3'>
					<h3 className='text-base font-bold text-base-700'>Diagrama</h3>
					<div className='flex items-center gap-1'>
						<button
							type='button'
							onClick={zoomOut}
							disabled={zoom <= ZOOM_MIN}
							className='cursor-pointer flex items-center justify-center rounded text-sm font-bold text-base-500 hover:text-base-700 hover:bg-base-200 transition-colors disabled:opacity-30 disabled:pointer-events-none'
							title='Alejar'
						>
							−
						</button>
						<button
							type='button'
							onClick={zoomReset}
							className='cursor-pointer px-1.5 h-7 flex items-center justify-center rounded text-xs font-medium text-base-600 hover:text-base-800 hover:bg-base-200 transition-colors'
							title='Restablecer zoom'
						>
							{Math.round(zoom * 100)}%
						</button>
						<button
							type='button'
							onClick={zoomIn}
							disabled={zoom >= ZOOM_MAX}
							className='cursor-pointer flex items-center justify-center rounded text-sm font-bold text-base-500 hover:text-base-700 hover:bg-base-200 transition-colors disabled:opacity-30 disabled:pointer-events-none'
							title='Acercar'
						>
							+
						</button>
						<div className='w-px h-5 bg-base-300 mx-1' />
						<button
							type='button'
							className='cursor-pointer size-7 flex items-center justify-center rounded text-base-500 hover:text-base-700 hover:bg-base-200 transition-colors'
							onClick={isMaximized ? onMinimize : onMaximize}
							title={isMaximized ? 'Restablecer' : 'Expandir'}
						>
							{isMaximized ? <MinEditor size={24} /> : <MaxEditor size={24} />}
						</button>
					</div>
				</div>

				{(state === 'loading-engine' || state === 'rendering') && (
					<div className='flex items-center gap-2 text-base-500 text-sm py-8 justify-center'>
						<svg
							className='animate-spin size-5'
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
					<div className='bg-red-50 border border-red-200 rounded-sm p-3 text-red-700 text-sm'>
						<p className='font-medium mb-1'>Error al renderizar el diagrama</p>
						<p className='text-status-error text-xs font-mono'>{error}</p>
					</div>
				)}

				{state === 'done' && svg && (
					<div
						ref={viewportRef}
						onMouseDown={handlePanStart}
						onMouseMove={handlePanMove}
						onMouseUp={handlePanEnd}
						onMouseLeave={handlePanEnd}
						className={`relative overflow-hidden bg-white rounded-sm border border-base-200 ${isMaximized ? 'h-full' : ''} ${isPanning ? 'cursor-grabbing select-none' : 'cursor-grab'}`}
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
