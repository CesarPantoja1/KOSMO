import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
	plugins: [react()],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, './src'),
			app: path.resolve(__dirname, './app'),
		},
	},
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: './vitest.setup.ts',
		coverage: {
			provider: 'v8',
			reporter: ['text', 'html', 'lcov'],
			include: ['src/entities/**/*.{ts,tsx}', 'src/features/**/*.{ts,tsx}'],
			exclude: [
				'**/*.test.*',
				'**/index.ts',
				'src/**/ui/**',
			],
			thresholds: {
				lines: 65,
				statements: 65,
				functions: 60,
				branches: 55,
			},
		},
	},
});
