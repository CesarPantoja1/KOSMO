import type { Config } from 'tailwindcss';

const config: Config = {
	content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './src/**/*.{js,ts,jsx,tsx,mdx}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Base/Background colors
				bg: {
					base: 'hsl(var(--color-bg-base) / <alpha-value>)',
					subtle: 'hsl(var(--color-bg-subtle) / <alpha-value>)',
					elevated: 'hsl(var(--color-bg-elevated) / <alpha-value>)',
				},
				// Text colors
				text: {
					primary: 'hsl(var(--color-text-primary) / <alpha-value>)',
					secondary: 'hsl(var(--color-text-secondary) / <alpha-value>)',
					tertiary: 'hsl(var(--color-text-tertiary) / <alpha-value>)',
				},
				// Border colors
				border: {
					DEFAULT: 'hsl(var(--color-border-default) / <alpha-value>)',
					strong: 'hsl(var(--color-border-strong) / <alpha-value>)',
				},
				// Accent colors
				accent: {
					primary: 'hsl(var(--color-accent-primary) / <alpha-value>)',
					'primary-hover': 'hsl(var(--color-accent-primary-hover) / <alpha-value>)',
				},
				// Status colors
				status: {
					approved: 'hsl(var(--color-status-approved) / <alpha-value>)',
					'approved-bg': 'hsl(var(--color-status-approved-bg) / <alpha-value>)',
					stale: 'hsl(var(--color-status-stale) / <alpha-value>)',
					'stale-bg': 'hsl(var(--color-status-stale-bg) / <alpha-value>)',
					error: 'hsl(var(--color-status-error) / <alpha-value>)',
					'error-bg': 'hsl(var(--color-status-error-bg) / <alpha-value>)',
					info: 'hsl(var(--color-status-info) / <alpha-value>)',
					'info-bg': 'hsl(var(--color-status-info-bg) / <alpha-value>)',
					generating: 'hsl(var(--color-status-generating) / <alpha-value>)',
					'generating-bg': 'hsl(var(--color-status-generating-bg) / <alpha-value>)',
				},
			},
			borderRadius: {
				sm: 'var(--radius-sm)',
				md: 'var(--radius-md)',
				lg: 'var(--radius-lg)',
			},
			boxShadow: {
				sm: 'var(--shadow-sm)',
				md: 'var(--shadow-md)',
				lg: 'var(--shadow-lg)',
			},
			height: {
				topbar: 'var(--topbar-h)',
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
				mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
			},
			animation: {
				'fade-in': 'fade-in 0.2s ease forwards',
				'slide-down': 'slide-down 0.15s ease forwards',
				'fade-scale': 'fade-scale-in 0.2s ease forwards',
				'node-appear': 'node-appear 0.3s ease forwards',
				'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				shimmer: 'shimmer 1.4s infinite',
				wobble: 'wobble 0.5s ease-in-out',
			},
			keyframes: {
				'fade-in': {
					from: {
						opacity: '0',
						transform: 'translateY(-6px)',
					},
					to: {
						opacity: '1',
						transform: 'translateY(0)',
					},
				},
				'slide-down': {
					from: {
						transform: 'translateY(-100%)',
						opacity: '0',
					},
					to: {
						transform: 'translateY(0)',
						opacity: '1',
					},
				},
				'fade-scale-in': {
					from: {
						opacity: '0',
						transform: 'scale(0.96)',
					},
					to: {
						opacity: '1',
						transform: 'scale(1)',
					},
				},
				'node-appear': {
					from: {
						opacity: '0',
						transform: 'scale(0.7)',
					},
					to: {
						opacity: '1',
						transform: 'scale(1)',
					},
				},
				'pulse-ring': {
					'0%, 100%': {
						opacity: '1',
					},
					'50%': {
						opacity: '0.4',
					},
				},
				shimmer: {
					'0%': {
						'background-position': '-400px 0',
					},
					'100%': {
						'background-position': '400px 0',
					},
				},
				wobble: {
					'0%, 100%': {
						transform: 'rotate(0)',
					},
					'20%': {
						transform: 'rotate(-3deg)',
					},
					'60%': {
						transform: 'rotate(3deg)',
					},
					'80%': {
						transform: 'rotate(-1.5deg)',
					},
				},
			},
		},
	},
	plugins: [],
};

export default config;
