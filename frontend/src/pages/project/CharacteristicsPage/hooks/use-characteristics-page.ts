'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from 'app/store/app.store';
import { useCharacteristicStore, type CharacteristicResponse } from '@/entities/characteristic';
import { toast } from '@/shared/ui';

interface UseCharacteristicsPageReturn {
	characteristics: CharacteristicResponse[];
	isLoading: boolean;
	hasCharacteristics: boolean;
	searchQuery: string;
	setSearchQuery: (v: string) => void;
	filtered: CharacteristicResponse[];
	refetch: () => Promise<void>;
}

export function useCharacteristicsPage(): UseCharacteristicsPageReturn {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [isLoading, setIsLoading] = useState(true);
	const [searchQuery, setSearchQuery] = useState('');

	const characteristics = useCharacteristicStore((s) => s.currentCharacteristics);
	const storeGetCharacteristics = useCharacteristicStore((s) => s.getCharacteristics);

	const fetchData = async () => {
		if (!currentProject) return;

		try {
			await storeGetCharacteristics(currentProject.id);
		} catch (err) {
			const errorStatus =
				err && typeof err === 'object' && 'status' in err
					? (err as { status: unknown }).status
					: undefined;
			const errorMessage = err instanceof Error ? err.message : '';
			if (
				errorStatus === 404 ||
				errorMessage.includes('404') ||
				errorMessage.includes('no existe')
			) {
				useCharacteristicStore.setState({ currentCharacteristics: [] });
			} else {
				toast.error(errorMessage || 'Error al cargar las características');
			}
		} finally {
			setIsLoading(false);
		}
	};

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		fetchData();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [currentProject, router]);

	const hasCharacteristics = characteristics.length > 0;

	const filtered = searchQuery.trim()
		? characteristics.filter((c) =>
				c.title.toLowerCase().includes(searchQuery.toLowerCase()),
			)
		: characteristics;

	return { characteristics, isLoading, hasCharacteristics, searchQuery, setSearchQuery, filtered, refetch: fetchData };
}
