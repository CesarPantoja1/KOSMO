'use client';

import {
	UNSTABLE_ToastRegion,
	UNSTABLE_ToastList,
	UNSTABLE_Toast,
	UNSTABLE_ToastContent,
	Button,
} from 'react-aria-components';
import { Text } from 'react-aria-components/Toast';
import type { ToastPosition, ToastContent } from './types';
import type { QueuedToast } from 'react-aria-components/Toast';
import { queue } from './toast';
import { CheckIcon, ErrorIcon, WarningIcon, InfoIcon, CloseIcon } from './icons';

type ToasterProviderProps = {
	position?: ToastPosition;
};

const positionStyles: Record<ToastPosition, string> = {
	'top-right': 'fixed top-4 right-4 z-50 flex flex-col gap-2 w-80',
	'top-left': 'fixed top-4 left-4 z-50 flex flex-col gap-2 w-80',
	'bottom-right': 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80',
	'bottom-left': 'fixed bottom-4 left-4 z-50 flex flex-col gap-2 w-80',
	'top-center': 'fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-80',
	'bottom-center':
		'fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-80',
};

const variantConfig = {
	success: {
		icon: CheckIcon,
		iconBg: 'bg-success-50',
		iconColor: 'text-success-700',
		borderColor: 'border-success-500/20',
		titleColor: 'text-success-700',
	},
	error: {
		icon: ErrorIcon,
		iconBg: 'bg-error-50',
		iconColor: 'text-error-700',
		borderColor: 'border-error-500/20',
		titleColor: 'text-error-700',
	},
	warning: {
		icon: WarningIcon,
		iconBg: 'bg-warning-50',
		iconColor: 'text-warning-700',
		borderColor: 'border-warning-500/20',
		titleColor: 'text-warning-700',
	},
	info: {
		icon: InfoIcon,
		iconBg: 'bg-info-50',
		iconColor: 'text-info-700',
		borderColor: 'border-info-500/20',
		titleColor: 'text-info-700',
	},
} as const;

function ToastItem({ toastItem }: { toastItem: { toast: QueuedToast<ToastContent> } }) {
	const { content } = toastItem.toast;
	const config = variantConfig[content.variant];
	const Icon = config.icon;

	return (
		<UNSTABLE_Toast toast={toastItem.toast}>
			<div
				className={`flex items-start gap-3 rounded-lg border bg-neutral-0 ${config.borderColor} p-4 shadow-sm`}
			>
				<span
					className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${config.iconBg}`}
				>
					<Icon className={`h-4 w-4 ${config.iconColor}`} />
				</span>
				<UNSTABLE_ToastContent className='min-w-0 flex-1'>
					{content.title && (
						<Text slot='title' className={`text-sm font-semibold ${config.titleColor}`}>
							{content.title}
						</Text>
					)}
					<Text slot='description' className='text-sm text-neutral-500'>
						{content.message}
					</Text>
				</UNSTABLE_ToastContent>
				{content.action && (
					<Button
						onPress={() => {
							content.action?.onAction();
							queue.close(toastItem.toast.key);
						}}
						className='shrink-0 cursor-pointer rounded-md px-2 py-1 text-xs font-semibold text-primary-600 transition-colors hover:bg-primary-50'
					>
						{content.action.label}
					</Button>
				)}
				<Button slot='close' className='cursor-pointer rounded-md p-1 text-neutral-400 transition-colors hover:text-neutral-600'>
					<CloseIcon className='h-4 w-4' />
				</Button>
			</div>
		</UNSTABLE_Toast>
	);
}

export function ToasterProvider({ position = 'top-right' }: ToasterProviderProps) {
	return (
		<UNSTABLE_ToastRegion queue={queue} className={positionStyles[position]}>
			<UNSTABLE_ToastList>
				{({ toast: toastItem }: { toast: QueuedToast<ToastContent> }) => (
					<ToastItem key={toastItem.key} toastItem={{ toast: toastItem }} />
				)}
			</UNSTABLE_ToastList>
		</UNSTABLE_ToastRegion>
	);
}
