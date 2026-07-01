import Load from './icons/Load';

type Props = {
	title: string;
	description: string;
};

const Loading = ({ title, description }: Props) => {
	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm'>
			<div className='w-full max-w-2xl rounded-xl bg-base-50 p-10 shadow-2xl outline outline-base-800'>
				<div className='flex flex-col items-center gap-8 text-center'>
					<div className='space-y-3'>
						<h2 className='text-2xl font-semibold text-black'>{title}</h2>
						<p className='text-base text-base-700'>{description}</p>
					</div>
					<div className='animate-spin-custom'>
						<Load color='text-ai' />
					</div>
					<span className='font-mono text-sm text-ai'>Cargando</span>
				</div>
			</div>
		</div>
	);
};

export default Loading;
