'use client';

import { useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { addCharacteristics } from '@/entities/characteristic';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

const characteristicSchema = z.object({
	title: z.string().max(50, 'Máximo 50 caracteres'),
	description: z.string().max(500, 'Máximo 500 caracteres'),
});

type CharacteristicFormData = z.infer<typeof characteristicSchema>;

interface UseCreateCharacteristicReturn {
	titleValue: string;
	titleOnBlur: () => void;
	titleRef: React.Ref<HTMLInputElement>;
	descValue: string;
	descOnBlur: () => void;
	descRef: React.Ref<HTMLTextAreaElement>;
	titleCount: number;
	descCount: number;
	titleOver: boolean;
	descOver: boolean;
	fieldErrors: { title: boolean; description: boolean };
	showSuggestionsModal: boolean;
	openSuggestionsModal: () => void;
	closeSuggestionsModal: () => void;
	handleTitleChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	handleDescChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
	handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
	applySuggestion: (title: string, description: string) => void;
}

export function useCreateCharacteristic(
	onCreated?: () => void,
): UseCreateCharacteristicReturn {
	const projectId = useAppStore((s) => s.currentProject?.id);
	const { control, handleSubmit: formSubmit, setValue } = useForm<CharacteristicFormData>({
		mode: 'onChange',
		resolver: zodResolver(characteristicSchema),
		defaultValues: { title: '', description: '' },
	});

	const {
		field: {
			value: titleValue,
			onChange: titleOnChange,
			onBlur: titleOnBlur,
			ref: titleRef,
		},
	} = useController({ name: 'title', control });

	const {
		field: { value: descValue, onChange: descOnChange, onBlur: descOnBlur, ref: descRef },
	} = useController({ name: 'description', control });

	const [showSuggestionsModal, setShowSuggestionsModal] = useState(false);
	const [fieldErrors, setFieldErrors] = useState<{ title: boolean; description: boolean }>({
		title: false,
		description: false,
	});

	const titleCount = titleValue.length;
	const descCount = descValue.length;
	const titleOver = titleCount > 50;
	const descOver = descCount > 500;

	const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		titleOnChange(e);
		if (fieldErrors.title) setFieldErrors((p) => ({ ...p, title: false }));
	};

	const handleDescChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		descOnChange(e);
		if (fieldErrors.description) setFieldErrors((p) => ({ ...p, description: false }));
	};

	const onSubmit = async (data: CharacteristicFormData) => {
		const hasTitleError = !data.title || data.title.length > 50;
		const hasDescError = !data.description || data.description.length > 500;
		if (hasTitleError || hasDescError) {
			setFieldErrors({ title: hasTitleError, description: hasDescError });
			return;
		}
		if (!projectId) return;
		try {
			await addCharacteristics(projectId, [
				{
					title: data.title,
					description: data.description,
					rationale: '',
				},
			]);
			onCreated?.();
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al crear la característica';
			toast.error(message);
		}
	};

	const applySuggestion = (title: string, description: string) => {
		setValue('title', title);
		setValue('description', description);
		setShowSuggestionsModal(false);
	};

	return {
		titleValue,
		titleOnBlur,
		titleRef,
		descValue,
		descOnBlur,
		descRef,
		titleCount,
		descCount,
		titleOver,
		descOver,
		fieldErrors,
		showSuggestionsModal,
		openSuggestionsModal: () => setShowSuggestionsModal(true),
		closeSuggestionsModal: () => setShowSuggestionsModal(false),
		handleTitleChange,
		handleDescChange,
		handleSubmit: formSubmit(onSubmit),
		applySuggestion,
	};
}
