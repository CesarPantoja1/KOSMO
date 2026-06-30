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
import { CheckIcon, ErrorIcon, WarningIcon, InfoIcon } from './icons';
import Close from '../icons/Close';

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
		iconColor: 'text-base-50',
		toastBg: 'bg-primary-100',
		borderColor: 'border-base-950',
	},
	error: {
		icon: ErrorIcon,
		iconColor: 'text-base-50',
		toastBg: 'bg-status-error',
		borderColor: 'border-red-200',
	},
	warning: {
		icon: WarningIcon,
		iconColor: 'text-base-50',
		toastBg: 'bg-status-warning',
		borderColor: 'border-amber-200',
	},
	info: {
		icon: InfoIcon,
		iconColor: 'text-base-50',
		toastBg: 'bg-status-info',
		borderColor: 'border-blue-200',
	},
} as const;

function ToastItem({ toastItem }: { toastItem: { toast: QueuedToast<ToastContent> } }) {
	const { content } = toastItem.toast;
	const config = variantConfig[content.variant];
	//const Icon = config.icon;

	return (
		<UNSTABLE_Toast toast={toastItem.toast}>
			<div
				className={`flex items-start gap-3 rounded-lg border ${config.borderColor} ${config.toastBg} p-4 shadow-lg`}
			>
				{/*
				<span
					className={`flex size-8 shrink-0 items-center justify-center rounded-full ${config.iconBg} ${config.iconColor}`}
				>
					<Icon className='size-5' />
				</span>
				*/}
				<UNSTABLE_ToastContent className='min-w-0 flex-1'>
					{content.title && (
						<Text slot='title' className='text-sm font-semibold text-base-600'>
							{content.title}
						</Text>
					)}
					<Text slot='description' className='text-sm text-base-50'>
						{content.message}
					</Text>
				</UNSTABLE_ToastContent>
				<Button slot='close' className='cursor-pointer'>
					<Close color='text-base-50' size={24} />
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
