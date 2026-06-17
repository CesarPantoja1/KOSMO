import type { Config } from 'tailwindcss';
import typography from '@tailwindcss/typography';

const config: Config = {
	content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './src/**/*.{js,ts,jsx,tsx,mdx}'],
	darkMode: 'class',
	theme: {},
	plugins: [typography],
};

export default config;
