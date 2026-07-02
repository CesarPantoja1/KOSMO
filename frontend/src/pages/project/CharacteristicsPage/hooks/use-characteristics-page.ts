'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from 'app/store/app.store';
import { getCharacteristics } from '@/entities/characteristic';
import { toast } from '@/shared/ui';
import type { Characteristic } from '@/entities/characteristic';

interface UseCharacteristicsPageReturn {
	view: 'list' | 'create';
	setView: (v: 'list' | 'create') => void;
	characteristics: Characteristic[];
	isLoading: boolean;
	searchQuery: string;
	setSearchQuery: (v: string) => void;
	filtered: Characteristic[];
}

export function useCharacteristicsPage(): UseCharacteristicsPageReturn {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [view, setView] = useState<'list' | 'create'>('list');
	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [searchQuery, setSearchQuery] = useState('');

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetchData = async () => {
			try {
				const data = await getCharacteristics(currentProject.id);
				setCharacteristics(data);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : 'Error al cargar las características';
				toast.error(message);
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [currentProject, router]);

	const filtered = searchQuery.trim()
		? characteristics.filter((c) =>
				c.title.toLowerCase().includes(searchQuery.toLowerCase()),
			)
		: characteristics;

	return { view, setView, characteristics, isLoading, searchQuery, setSearchQuery, filtered };
}
