'use client';

import { useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { addCharacteristic } from '@/entities/characteristic';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';

const characteristicSchema = z.object({
	title: z
		.string()
		.max(50, 'Máximo 50 caracteres')
		.regex(/^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]*$/, 'Solo se permiten letras y espacios'),
	description: z
		.string()
		.max(500, 'Máximo 500 caracteres')
		.regex(
			/^[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ\s.,:;\-()¿?¡!]*$/,
			'Solo se permiten letras, números y signos de puntuación básicos',
		),
});

type CharacteristicFormData = z.infer<typeof characteristicSchema>;

interface FieldError {
	title: string;
	description: string;
}

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
	fieldErrors: FieldError;
	showSuggestionsModal: boolean;
	openSuggestionsModal: () => void;
	closeSuggestionsModal: () => void;
	handleTitleChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	handleDescChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
	handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
	handleCancel: () => void;
	applySuggestion: (title: string, description: string) => void;
	showConsistencyModal: boolean;
	consistencyInfo: { origin: string; reason: string } | null;
	isValidating: boolean;
	handleForceCreate: () => void;
	closeConsistencyModal: () => void;
}

function validateField(value: string, maxLength: number): string {
	const trimmed = value.trim();
	if (trimmed.length === 0) return 'Este campo es obligatorio';
	if (value.length > maxLength) return `Máximo ${maxLength} caracteres`;
	return '';
}

export function useCreateCharacteristic(
	onCreated?: () => void,
): UseCreateCharacteristicReturn {
	const projectId = useAppStore((s) => s.currentProject?.id);
	const router = useRouter();
	const {
		control,
		handleSubmit: formSubmit,
		setValue,
	} = useForm<CharacteristicFormData>({
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
	const [showConsistencyModal, setShowConsistencyModal] = useState(false);
	const [isValidating, setIsValidating] = useState(false);
	const [consistencyInfo, setConsistencyInfo] = useState<{
		origin: string;
		reason: string;
	} | null>(null);
	const [fieldErrors, setFieldErrors] = useState<FieldError>({
		title: '',
		description: '',
	});

	const titleCount = titleValue.length;
	const descCount = descValue.length;
	const titleOver = titleCount > 50;
	const descOver = descCount > 500;

	const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const sanitizedValue = e.target.value.replace(/[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]/g, '');
		const syntheticEvent = {
			...e,
			target: { ...e.target, value: sanitizedValue, name: e.target.name },
		};
		titleOnChange(syntheticEvent);
		if (fieldErrors.title) setFieldErrors((p) => ({ ...p, title: '' }));
	};

	const handleDescChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		const sanitizedValue = e.target.value.replace(
			/[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ\s.,:;\-()¿?¡!]/g,
			'',
		);
		const syntheticEvent = {
			...e,
			target: { ...e.target, value: sanitizedValue, name: e.target.name },
		};
		descOnChange(syntheticEvent);
		if (fieldErrors.description) setFieldErrors((p) => ({ ...p, description: '' }));
	};

	const onSubmit = async (data: CharacteristicFormData) => {
		const titleError = validateField(data.title, 50);
		const descError = validateField(data.description, 500);
		if (titleError || descError) {
			setFieldErrors({ title: titleError, description: descError });
			return;
		}
		if (!projectId) return;
		setIsValidating(true);
		try {
			const result = await addCharacteristic(projectId, {
				title: data.title,
				description: data.description,
			});
			setIsValidating(false);

			if (result.is_saved) {
				onCreated?.();
			} else {
				setConsistencyInfo({
					origin: result.origin || '',
					reason: result.inconsistency_reason || '',
				});
				setShowConsistencyModal(true);
			}
		} catch (err) {
			setIsValidating(false);
			const message =
				err instanceof Error
					? err.message
					: 'No se pudo guardar la característica. Intenta nuevamente.';
			toast.error(message);
		}
	};

	const handleForceCreate = async () => {
		if (!projectId || !consistencyInfo) return;
		try {
			const result = await addCharacteristic(projectId, {
				title: titleValue,
				description: descValue,
				origin: consistencyInfo.origin,
				force: true,
			});
			if (result.is_saved) {
				setShowConsistencyModal(false);
				onCreated?.();
			}
		} catch (err) {
			toast.error('No se pudo forzar la creación.');
		}
	};

	const handleCancel = () => {
		router.push('/proyecto/caracteristicas');
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
		handleCancel,
		applySuggestion,
		showConsistencyModal,
		consistencyInfo,
		isValidating,
		handleForceCreate,
		closeConsistencyModal: () => setShowConsistencyModal(false),
	};
}
