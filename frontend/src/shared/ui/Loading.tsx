import { useEffect, useState } from 'react';
import Load from './icons/Load';

type Props = {
	title: string;
	description: string;
	messages?: string[];
};

const DEFAULT_MESSAGES = ['Cargando'];

const Loading = ({ title, description, messages = DEFAULT_MESSAGES }: Props) => {
	const [messageIndex, setMessageIndex] = useState(0);

	useEffect(() => {
		if (messages.length <= 1) return;

		const interval = setInterval(() => {
			setMessageIndex((prev) => (prev < messages.length - 1 ? prev + 1 : prev));
		}, 10000);

		return () => clearInterval(interval);
	}, [messages]);

	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/40'>
			<div className='w-full max-w-lg rounded-xl bg-neutral-0 p-10 shadow-xl'>
				<div className='flex flex-col items-center gap-8 text-center'>
					<div className='space-y-2'>
						<h2 className='text-xl font-semibold text-neutral-800'>{title}</h2>
						<p className='text-sm text-neutral-500'>{description}</p>
					</div>
					<div className='animate-spin-custom'>
						<Load color='text-ai-500' />
					</div>
					<span className='text-sm text-neutral-400'>{messages[messageIndex]}</span>
				</div>
			</div>
		</div>
	);
};

export default Loading;
