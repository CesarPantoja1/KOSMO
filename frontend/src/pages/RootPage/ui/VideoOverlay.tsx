'use client';

interface VideoOverlayProps {
	isOpen: boolean;
	onClose: () => void;
}

export function VideoOverlay({ isOpen, onClose }: VideoOverlayProps) {
	if (!isOpen) return null;

	return (
		<div className='fixed inset-0 z-[9999] bg-black flex items-center justify-center'>
			<video
				src='/kosmo_intruduction.mp4'
				autoPlay
				playsInline
				className='w-full h-full object-contain'
				onEnded={() => {
					setTimeout(onClose, 5000);
				}}
			/>
		</div>
	);
}
