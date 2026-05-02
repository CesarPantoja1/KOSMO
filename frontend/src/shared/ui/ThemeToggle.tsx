'use client';

import React from 'react';
import { useTheme } from '@/shared/ui';

/**
 * Example Theme Toggle component showing how to use useTheme hook
 * Can be added to a navbar or settings panel
 */
export function ThemeToggle() {
	const { theme, toggleTheme } = useTheme();

	return (
		<button
			onClick={toggleTheme}
			className='btn btn-ghost'
			aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
			title={`Current theme: ${theme}`}
		>
			{theme === 'light' ? '🌙' : '☀️'}
			<span className='hidden sm:inline ml-1'>
				{theme === 'light' ? 'Dark' : 'Light'} Mode
			</span>
		</button>
	);
}
