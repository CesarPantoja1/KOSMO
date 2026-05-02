'use client';

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

interface ThemeContextType {
	theme: 'light' | 'dark';
	toggleTheme: () => void;
	setTheme: (theme: 'light' | 'dark') => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [theme, setThemeState] = useState<'light' | 'dark'>('light');
	const [mounted, setMounted] = useState(false);

	// Initialize theme from localStorage or system preference
	useEffect(() => {
		const storedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;

		if (storedTheme) {
			setThemeState(storedTheme);
		} else {
			// Default to light theme or detect from system
			const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
			setThemeState(prefersDark ? 'dark' : 'light');
		}

		setMounted(true);
	}, []);

	// Apply theme to DOM
	useEffect(() => {
		if (!mounted) return;

		const html = document.documentElement;

		if (theme === 'dark') {
			html.setAttribute('data-theme', 'dark');
			html.classList.add('dark');
		} else {
			html.removeAttribute('data-theme');
			html.classList.remove('dark');
		}

		localStorage.setItem('theme', theme);
	}, [theme, mounted]);

	const toggleTheme = () => {
		setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
	};

	const setTheme = (newTheme: 'light' | 'dark') => {
		setThemeState(newTheme);
	};

	// Prevent hydration mismatch by not rendering until mounted
	if (!mounted) {
		return <>{children}</>;
	}

	return (
		<ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
			{children}
		</ThemeContext.Provider>
	);
}

export function useTheme() {
	const context = useContext(ThemeContext);
	if (context === undefined) {
		throw new Error('useTheme must be used within a ThemeProvider');
	}
	return context;
}
