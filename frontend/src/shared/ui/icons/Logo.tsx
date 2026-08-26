interface LogoProps {
	size?: number;
	className?: string;
}

import image from '../../../../public/kosmo.png';

export function Logo({ size = 36, className = '' }: LogoProps) {
	return (
		<div
			className={`flex items-center justify-center rounded-xl bg-linear-to-br from-ai-500 to-ai-600 font-bold text-neutral-0 ${className}`}
			style={{ width: size, height: size, fontSize: size * 0.44 }}
		>
			<img src={image.src} alt='image' className='bg-transparent' />
		</div>
	);
}
