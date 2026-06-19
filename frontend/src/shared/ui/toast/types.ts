export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export type ToastPosition =
	| 'top-right'
	| 'top-left'
	| 'bottom-right'
	| 'bottom-left'
	| 'top-center'
	| 'bottom-center';

export type ToastContent = {
	variant: ToastVariant;
	message: string;
	title?: string;
};

export type ToastOptions = {
	onClose?: () => void;
	timeout?: number;
};
