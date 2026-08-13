'use client';

import { useState, useEffect } from 'react';
import { getSuggestCharacteristics } from '@/entities/characteristic';
import { useProjectStore } from '@/entities/project';
import type { SuggestCharacteristic } from '@/entities/characteristic';

interface UseCharacteristicModalReturn {
	alternatives: SuggestCharacteristic[];
	selectedId: number | null;
	isLoading: boolean;
	hasError: boolean;
	handleCardClick: (id: number) => void;
	handleApply: () => void;
}

export function useCharacteristicModal(
	onApply: (selected: SuggestCharacteristic) => void,
): UseCharacteristicModalReturn {
	const projectId = useProjectStore((s) => s.currentProject?.id);
	const [alternatives, setAlternatives] = useState<SuggestCharacteristic[]>([]);
	const [selectedId, setSelectedId] = useState<number | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);

	useEffect(() => {
		if (!projectId) return;
		const fetch = async () => {
			setIsLoading(true);
			setHasError(false);
			try {
				const data = await getSuggestCharacteristics(projectId);
				setAlternatives(data);
			} catch {
				setHasError(true);
			} finally {
				setIsLoading(false);
			}
		};
		fetch();
	}, [projectId]);

	const handleCardClick = (id: number) => {
		setSelectedId((prev) => (prev === id ? null : id));
	};

	const handleApply = () => {
		const selected = alternatives.find((a) => a.number === selectedId);
		if (!selected) return;
		onApply(selected);
	};

	return { alternatives, selectedId, isLoading, hasError, handleCardClick, handleApply };
}
