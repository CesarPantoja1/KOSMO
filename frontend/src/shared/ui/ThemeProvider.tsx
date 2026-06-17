'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
	theme: Theme;
	toggleTheme: () => void;
	setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const getInitialTheme = (): Theme => {
	if (typeof window === 'undefined') {
		return 'light';
	}

	const storedTheme = localStorage.getItem('theme');
	if (storedTheme === 'light' || storedTheme === 'dark') {
		return storedTheme;
	}

	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [theme, setThemeState] = useState<Theme>(getInitialTheme);

	// Apply theme to DOM
	useEffect(() => {
		const html = document.documentElement;

		if (theme === 'dark') {
			html.setAttribute('data-theme', 'dark');
			html.classList.add('dark');
		} else {
			html.removeAttribute('data-theme');
			html.classList.remove('dark');
		}

		localStorage.setItem('theme', theme);
	}, [theme]);

	const toggleTheme = () => {
		setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
	};

	const setTheme = (newTheme: Theme) => {
		setThemeState(newTheme);
	};

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
