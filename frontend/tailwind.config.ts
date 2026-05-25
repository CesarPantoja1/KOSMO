import type { Config } from 'tailwindcss';

const config: Config = {
	content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './src/**/*.{js,ts,jsx,tsx,mdx}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				obsidian: {
					DEFAULT: '#0f172a',
					base: '#0f172a',
					hover: '#000004',
					active: '#000000',
					disabled: '#0f172a80',
				},
				snow: {
					DEFAULT: '#fafafa',
					base: '#fafafa',
					hover: '#d4d4d4',
					active: '#bababa',
					disabled: '#fafafa80',
				},
				forestgreen: {
					base: '#03593f',
					hover: '#003319',
					active: '#001900',
					disabled: '#03593f80',
				},
				success: {
					DEFAULT: '#10b981',
					base: '#10b981',
					hover: '#00935b',
					active: '#007941',
					disabled: '#10b98180',
				},
				warning: {
					DEFAULT: '#f59e0b',
					base: '#f59e0b',
					hover: '#cf7800',
					active: '#b55e00',
					disabled: '#f59e0b80',
				},
				error: {
					DEFAULT: '#e11d48',
					base: '#e11d48',
					hover: '#bb0022',
					active: '#a10008',
					disabled: '#e11d4880',
				},
				ai: {
					DEFAULT: '#6366f1',
					base: '#6366f1',
					hover: '#3d40cb',
					active: '#2326b1',
					disabled: '#6366f180',
				},
				mistgrey: {
					DEFAULT: '#e5e7eb',
					base: '#e5e7eb',
					hover: '#bfc1c5',
					active: '#a5a7ab',
					disabled: '#e5e7eb80',
				},
				darkgrey: {
					DEFAULT: '#96989b',
					base: '#96989b',
					hover: '#707275',
					active: '#56585b',
					disabled: '#96989b80',
				},
				light: {
					green: '#ebf9f3',
					yellow: '#ffe1ad',
				},
			},
			fontFamily: {
				geist: {
					'0': 'Geist',
					'1': 'sans-serif',
				},
				'geist-mono': {
					'0': 'Geist Mono',
					'1': 'sans-serif',
				},
			},
			fontSize: {
				'token-font-title': {
					'0': '32px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '700',
					},
				},
				'token-font-subtitle': {
					'0': '24px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '600',
					},
				},
				'token-font-header': {
					'0': '20px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '600',
					},
				},
				'token-font-tabs': {
					'0': '18px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '500',
					},
				},
				'token-font-normal': {
					'0': '16px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '400',
					},
				},
				'token-font-small': {
					'0': '14px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '400',
					},
				},
				'token-font-chips': {
					'0': '12px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '400',
					},
				},
				'token-font-button': {
					'0': '16px',
					'1': {
						lineHeight: 'normal',
						letterSpacing: '0.0000em',
						fontWeight: '400',
					},
				},
			},
			spacing: {
				token: {
					borders: {
						thickness: {
							border: {
								'4': '4px',
								'8': '8px',
							},
						},
					},
					shadows: {
						shadow: {
							blur: '8px',
							offset: {
								y: '4px',
								x: '0px',
							},
						},
					},
				},
			},
			borderRadius: {
				token: {
					border: {
						radius: {
							rounded: {
								md: '6px',
								lg: '8px',
								xl: '12px',
								full: '9999px',
							},
						},
					},
				},
			},
		},
	},
	plugins: [],
};

export default config;
