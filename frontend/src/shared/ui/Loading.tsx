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
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50'>
			<div className='w-full max-w-2xl rounded-xl bg-base-50 p-10 shadow-2xl outline outline-base-800'>
				<div className='flex flex-col items-center gap-8 text-center'>
					<div className='space-y-3'>
						<h2 className='text-2xl font-semibold text-black'>{title}</h2>
						<p className='text-base text-base-700'>{description}</p>
					</div>
					<div className='animate-spin-custom'>
						<Load color='text-ai' />
					</div>
					<span className='font-mono text-sm text-ai'>{messages[messageIndex]}</span>
				</div>
			</div>
		</div>
	);
};

export default Loading;
