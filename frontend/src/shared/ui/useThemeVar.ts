/**
 * Hook utility to get CSS variable values from the current theme
 * Usage: const bgColor = useThemeVar('--color-bg-base');
 */
export function useThemeVar(varName: string): string {
	if (typeof window === 'undefined') {
		return '';
	}

	const root = document.documentElement;
	const value = getComputedStyle(root).getPropertyValue(varName).trim();
	return value;
}

/**
 * Helper to convert HSL CSS variables to various formats
 * Usage: const rgb = hslToRgb('217', '98%', '54%')
 */
export function hslToRgb(h: string, s: string, l: string): string {
	const hsl = `hsl(${h} ${s} ${l})`;
	const ctx = document.createElement('canvas').getContext('2d');
	if (!ctx) return hsl;

	ctx.fillStyle = hsl;
	return ctx.fillStyle;
}

/**
 * Get a CSS variable as HSL values
 */
export function useThemeHsl(varName: string): { h: string; s: string; l: string } | null {
	const value = useThemeVar(varName);
	const match = value.match(
		/(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?%)(?:\/|$)/,
	);

	if (!match) {
		return null;
	}

	return {
		h: match[1],
		s: match[2],
		l: match[3],
	};
}
