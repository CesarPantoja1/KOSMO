'use client';

import {
	createContext,
	ReactNode,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useSyncExternalStore,
} from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
	theme: Theme;
	toggleTheme: () => void;
	setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);
const THEME_STORAGE_KEY = 'theme';
const THEME_CHANGE_EVENT = 'kosmo-theme-change';

function isTheme(value: string | null): value is Theme {
	return value === 'light' || value === 'dark';
}

function getStoredTheme(): Theme | null {
	if (typeof window === 'undefined') {
		return null;
	}

	const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
	return isTheme(storedTheme) ? storedTheme : null;
}

function getSystemTheme(): Theme {
	if (typeof window === 'undefined') {
		return 'light';
	}

	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getThemeSnapshot(): Theme {
	return getStoredTheme() ?? getSystemTheme();
}

function getServerThemeSnapshot(): Theme {
	return 'light';
}

function subscribeToThemeChanges(onStoreChange: () => void) {
	if (typeof window === 'undefined') {
		return () => {};
	}

	const handleStorage = (event: StorageEvent) => {
		if (event.key === THEME_STORAGE_KEY) {
			onStoreChange();
		}
	};
	const handleThemeChange = () => onStoreChange();
	const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
	const handleSystemThemeChange = () => {
		if (!getStoredTheme()) {
			onStoreChange();
		}
	};

	window.addEventListener('storage', handleStorage);
	window.addEventListener(THEME_CHANGE_EVENT, handleThemeChange);
	mediaQuery.addEventListener('change', handleSystemThemeChange);

	return () => {
		window.removeEventListener('storage', handleStorage);
		window.removeEventListener(THEME_CHANGE_EVENT, handleThemeChange);
		mediaQuery.removeEventListener('change', handleSystemThemeChange);
	};
}

function persistTheme(theme: Theme) {
	localStorage.setItem(THEME_STORAGE_KEY, theme);
	window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

export function ThemeProvider({ children }: { children: ReactNode }) {
	const theme = useSyncExternalStore(
		subscribeToThemeChanges,
		getThemeSnapshot,
		getServerThemeSnapshot,
	);

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
	}, [theme]);

	const toggleTheme = useCallback(() => {
		persistTheme(theme === 'light' ? 'dark' : 'light');
	}, [theme]);

	const setTheme = useCallback((newTheme: Theme) => {
		persistTheme(newTheme);
	}, []);

	const value = useMemo(() => ({ theme, toggleTheme, setTheme }), [theme, toggleTheme, setTheme]);

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
	const context = useContext(ThemeContext);
	if (context === undefined) {
		throw new Error('useTheme must be used within a ThemeProvider');
	}
	return context;
}
