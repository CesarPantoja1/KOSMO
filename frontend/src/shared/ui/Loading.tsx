'use client';
import { useEffect, useState } from 'react';

type Props = {
	title: string;
	description: string;
	messages?: string[] | string | null;
};

const DEFAULT_MESSAGES = ['Cargando'];

const Loading = ({ title, description, messages = DEFAULT_MESSAGES }: Props) => {
	const [messageIndex, setMessageIndex] = useState(0);

	const messagesArray = Array.isArray(messages) ? messages : messages ? [messages] : [];

	useEffect(() => {
		if (messagesArray.length <= 1) return;

		const interval = setInterval(() => {
			setMessageIndex((prev) => (prev < messagesArray.length - 1 ? prev + 1 : prev));
		}, 10000);

		return () => clearInterval(interval);
	}, [messages, messagesArray.length]);

	const currentMessage = messagesArray[messageIndex] ?? messagesArray[0] ?? '';

	return (
		<div className='warning-popup'>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200'
				onClick={(e) => e.stopPropagation()}
			>
				<div className='flex flex-col items-center gap-6 text-center'>
					<div>
						<h3 className='text-lg font-semibold text-neutral-800 mb-2'>{title}</h3>
						<p className='text-sm text-neutral-500'>{description}</p>
					</div>
					<div className='h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />
					<span className='text-xs text-neutral-400'>{currentMessage}</span>
				</div>
			</div>
		</div>
	);
};

export default Loading;
