'use client';

import { getProjects, type Project } from '@/entities/project';
import { useEffect, useRef, useState } from 'react';
import { CreateProjectForm } from './CreateProjectForm';

const CreateProjectPage = () => {
	const [projects, setProjects] = useState<Project[]>([]);
	const [showForm, setShowForm] = useState(false);
	const [isLoading, setIsLoading] = useState(true);
	const videoRef = useRef<HTMLVideoElement>(null);

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				const data = await getProjects();
				setProjects(data);
			} catch (error) {
				console.error('Error fetching projects:', error);
			} finally {
				setIsLoading(false);
			}
		};
		fetchProjects();
	}, []);

	const handleLoadedData = () => {
		if (videoRef.current) {
			videoRef.current.playbackRate = 0.7;
		}
	};

	const handleVideoEnd = () => {
		setTimeout(() => {
			setShowForm(true);
		}, 3000);
	};

	const handleTimeUpdate = () => {
		const video = videoRef.current;
		if (!video) return;

		const remaining = video.duration - video.currentTime;
		if (remaining <= 3 && video.volume > 0) {
			video.volume = Math.max(0, video.volume - 0.02);
		}
	};

	if (isLoading) {
		return (
			<div className='flex items-center justify-center h-full'>
				<div className='animate-spin-custom h-8 w-8 border-2 border-primary-500 border-t-transparent rounded-full' />
			</div>
		);
	}

	const hasNoProjects = projects.length === 0;

	if (hasNoProjects && !showForm) {
		return (
			<video
				ref={videoRef}
				src='/kosmo_intruduction.mp4'
				autoPlay
				onLoadedData={handleLoadedData}
				onTimeUpdate={handleTimeUpdate}
				onEnded={handleVideoEnd}
				className='fixed inset-0 w-full h-full object-cover z-50'
			/>
		);
	}

	return (
		<div className={`page-container mt-6${hasNoProjects ? ' animate-fade-in' : ''}`}>
			<div className='page-header pb-4'>
				{/* Header row */}
				<div className='flex items-start justify-between gap-4'>
					<div className='flex flex-col gap-1'>
						<h1 className='text-neutral-800 text-lg md:text-xl font-bold'>Crear Proyecto</h1>
						<p className='text-neutral-500 text-sm md:text-base'>
							Define la idea central y los objetivos de tu aplicación. Una descripción
							clara le permitirá al asistente estructurar correctamente las etapas
							posteriores.
						</p>
					</div>
				</div>

				<CreateProjectForm />
			</div>
		</div>
	);
};

export { CreateProjectPage };
