'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { IntegrationProvider, IntegrationStatus } from '../model/types';
import {
	connectIntegration,
	disconnectIntegration,
	getIntegrationStatus,
} from '../api/api';
import { authApi } from '@/shared/api';
import { useAuthStore } from '@/shared/model';
import { formatApiError } from '@/shared/api/errors';
import { toast } from '@/shared/ui/toast/toast';

export interface UseOAuthIntegrationParams {
	provider: IntegrationProvider;
	label: string;
	messageType: string;
	buildAuthUrl: (redirectUri: string) => string;
	redirectUri: string;
	onStatusChange?: (status: IntegrationStatus) => void;
}

export function useOAuthIntegration({
	provider,
	label,
	messageType,
	buildAuthUrl,
	redirectUri,
	onStatusChange,
}: UseOAuthIntegrationParams) {
	const [status, setStatus] = useState<IntegrationStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const [actionLoading, setActionLoading] = useState(false);
	const popupRef = useRef<Window | null>(null);
	const processingCodeRef = useRef<string | null>(null);

	useEffect(() => {
		let cancelled = false;

		getIntegrationStatus(provider)
			.then((result) => {
				if (!cancelled) {
					setStatus(result);
					onStatusChange?.(result);
				}
			})
			.catch((err) => {
				if (!cancelled) {
					toast.error(
						formatApiError(
							err,
							`No se pudo verificar el estado de la integración con ${label}.`,
						),
					);
				}
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
	}, [provider, label, onStatusChange]);

	const handleOAuthMessage = useCallback(
		(event: MessageEvent) => {
			if (event.origin !== window.location.origin) return;
			if (event.data?.type === 'oauth-error') {
				toast.error(
					`Error en la autorización de ${label}: ${event.data.error || 'Acceso denegado'}`,
				);
				popupRef.current?.close();
				popupRef.current = null;
				return;
			}
			if (event.data?.type !== messageType) return;

			const code = event.data.code as string;
			if (!code || processingCodeRef.current === code) return;
			processingCodeRef.current = code;

			setActionLoading(true);
			connectIntegration(provider, {
				code,
				redirect_uri: redirectUri,
			})
				.then(async (result) => {
					setStatus(result);
					onStatusChange?.(result);
					toast.success(
						`Cuenta de ${label} vinculada como @${result.username ?? 'desconocido'}.`,
					);
					try {
						const updatedUser = await authApi.getMe();
						useAuthStore.getState().setUser(updatedUser);
					} catch {
						// Noop si falla la actualización de la tienda
					}
				})
				.catch((err) =>
					toast.error(
						formatApiError(
							err,
							`Error al vincular la cuenta de ${label}. Intenta de nuevo.`,
						),
					),
				)
				.finally(() => {
					setActionLoading(false);
					processingCodeRef.current = null;
				});

			popupRef.current?.close();
			popupRef.current = null;
		},
		[provider, label, messageType, redirectUri, onStatusChange],
	);

	useEffect(() => {
		window.addEventListener('message', handleOAuthMessage);
		return () => window.removeEventListener('message', handleOAuthMessage);
	}, [handleOAuthMessage]);

	const handleConnect = useCallback(() => {
		popupRef.current = window.open(
			buildAuthUrl(redirectUri),
			`oauth-${provider}`,
			'width=600,height=700',
		);
	}, [buildAuthUrl, redirectUri, provider]);

	const handleDisconnect = useCallback(() => {
		setActionLoading(true);
		disconnectIntegration(provider)
			.then(() => {
				const newStatus: IntegrationStatus = { provider, is_connected: false };
				setStatus(newStatus);
				onStatusChange?.(newStatus);
				toast.success(`Cuenta de ${label} desconectada.`);
			})
			.catch(() =>
				toast.error(`Error al desconectar la cuenta de ${label}. Intenta de nuevo.`),
			)
			.finally(() => setActionLoading(false));
	}, [provider, label, onStatusChange]);

	return {
		status,
		loading,
		actionLoading,
		isConnected: status?.is_connected ?? false,
		username: status?.username ?? null,
		handleConnect,
		handleDisconnect,
	};
}
