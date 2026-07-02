'use client';

import { useState, useEffect } from 'react';
import { getAlternativeCharacteristics } from '@/entities/characteristic';
import { useAppStore } from 'app/store/app.store';
import type { AlternativeCharacteristic } from '@/entities/characteristic';

interface UseCharacteristicModalReturn {
	alternatives: AlternativeCharacteristic[];
	selectedId: string | null;
	isLoading: boolean;
	hasError: boolean;
	handleCardClick: (id: string) => void;
	handleApply: () => void;
}

export function useCharacteristicModal(
	onApply: (selected: AlternativeCharacteristic) => void,
): UseCharacteristicModalReturn {
	const projectId = useAppStore((s) => s.currentProject?.id);
	const [alternatives, setAlternatives] = useState<AlternativeCharacteristic[]>([]);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);

	useEffect(() => {
		if (!projectId) return;
		const fetch = async () => {
			setIsLoading(true);
			setHasError(false);
			try {
				const data = await getAlternativeCharacteristics(projectId);
				setAlternatives(data);
			} catch {
				setHasError(true);
			} finally {
				setIsLoading(false);
			}
		};
		fetch();
	}, [projectId]);

	const handleCardClick = (id: string) => {
		setSelectedId((prev) => (prev === id ? null : id));
	};

	const handleApply = () => {
		const selected = alternatives.find((a) => a.id === selectedId);
		if (!selected) return;
		onApply(selected);
	};

	return { alternatives, selectedId, isLoading, hasError, handleCardClick, handleApply };
}
