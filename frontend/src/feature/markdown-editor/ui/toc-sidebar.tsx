'use client';

import { useState } from 'react';
import clsx from 'clsx';

import { HeadingItem } from '../types/heading';
import { CloseMarkdownContent, OpenMarkdownContent } from './icons';

interface Props {
	headings: HeadingItem[];
	activeId?: string;
}

export function TocSidebar({ headings, activeId }: Props) {
	const [isOpen, setIsOpen] = useState(true);

	const handleScroll = (id: string) => {
		const element = document.getElementById(id);

		if (!element) return;

		element.scrollIntoView({
			behavior: 'smooth',
			block: 'start',
		});
	};

	return (
		<aside
			className='sticky top-0 h-full shrink-0 overflow-y-auto border-r bg-snow transition-all duration-300'
			style={{ width: isOpen ? 280 : 48 }}
		>
			{isOpen ? (
				<>
					<div className='mb-6 flex items-center justify-between pt-4 px-4'>
						<h2 className='text-lg font-semibold uppercase tracking-wide'>Contenido</h2>
						<button onClick={() => setIsOpen(false)} className='cursor-pointer'>
							<CloseMarkdownContent />
						</button>
					</div>

					<nav className='space-y-1 px-4'>
						{headings.map((heading) => (
							<button
								key={heading.id}
								onClick={() => handleScroll(heading.id)}
								className={clsx(
									'block w-full rounded-md px-2 py-1 text-left text-sm transition-colors cursor-pointer',
									'hover:bg-neutral-800',
									activeId === heading.id
										? 'bg-neutral-800 text-white'
										: 'text-neutral-400',
								)}
								style={{
									paddingLeft: `${heading.depth * 12}px`,
								}}
							>
								{heading.text}
							</button>
						))}
					</nav>
				</>
			) : (
				<div className='flex justify-center pt-4'>
					<button onClick={() => setIsOpen(true)} className='cursor-pointer'>
						<OpenMarkdownContent />
					</button>
				</div>
			)}
		</aside>
	);
}
