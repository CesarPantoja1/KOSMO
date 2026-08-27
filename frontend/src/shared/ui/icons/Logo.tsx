import Image from 'next/image';

interface LogoProps {
	size?: number;
	className?: string;
}

export function Logo({ size = 36, className = '' }: LogoProps) {
	return (
		<div
			className={`flex items-center justify-center rounded-xl bg-linear-to-br from-ai-500 to-ai-600 font-bold text-neutral-0 ${className}`}
			style={{ width: size, height: size, fontSize: size * 0.44 }}
		>
			<Image
				src='/kosmo.png'
				alt='KOSMO Logo'
				width={size}
				height={size}
				className='bg-transparent'
			/>
		</div>
	);
}
