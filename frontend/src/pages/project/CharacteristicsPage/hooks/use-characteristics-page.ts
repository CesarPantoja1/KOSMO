'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useProjectStore } from '@/entities/project';
import {
	useCharacteristicStore,
	type CharacteristicResponse,
} from '@/entities/characteristic';
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
	const currentProject = useProjectStore((s) => s.currentProject);
	const router = useRouter();

	const [isLoading, setIsLoading] = useState(false);
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
		}
	};

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		if (characteristics.length === 0) {
			// eslint-disable-next-line react-hooks/set-state-in-effect
			setIsLoading(true);
			void fetchData().finally(() => setIsLoading(false));
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [currentProject, router]);

	const hasCharacteristics = characteristics.length > 0;

	const filtered = searchQuery.trim()
		? characteristics.filter((c) =>
				c.title.toLowerCase().includes(searchQuery.toLowerCase()),
			)
		: characteristics;

	return {
		characteristics,
		isLoading,
		hasCharacteristics,
		searchQuery,
		setSearchQuery,
		filtered,
		refetch: fetchData,
	};
}
