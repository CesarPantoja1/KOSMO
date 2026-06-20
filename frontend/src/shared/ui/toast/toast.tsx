import { UNSTABLE_ToastQueue } from 'react-aria-components';
import type { ToastContent, ToastOptions, ToastVariant } from './types';

const DEFAULT_TIMEOUT = 5000;

const queue = new UNSTABLE_ToastQueue<ToastContent>({
	maxVisibleToasts: 5,
});

function add(
	message: string,
	variant: ToastVariant,
	options?: ToastOptions,
	title?: string,
) {
	return queue.add(
		{ variant, message, title },
		{ timeout: DEFAULT_TIMEOUT, ...options },
	);
}

export const toast = {
	success: (message: string, options?: ToastOptions, title?: string) =>
		add(message, 'success', options, title),
	error: (message: string, options?: ToastOptions, title?: string) =>
		add(message, 'error', options, title),
	warning: (message: string, options?: ToastOptions, title?: string) =>
		add(message, 'warning', options, title),
	info: (message: string, options?: ToastOptions, title?: string) =>
		add(message, 'info', options, title),
	add: (content: ToastContent, options?: ToastOptions) =>
		queue.add(content, { timeout: DEFAULT_TIMEOUT, ...options }),
	close: (key: string) => queue.close(key),
};

export { queue };
