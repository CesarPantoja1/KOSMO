'use client';

import { useMemo } from 'react';

import { extractHeadings } from '../lib/extract-headings';

export function useHeadings(markdown: string) {
	return useMemo(() => {
		return extractHeadings(markdown);
	}, [markdown]);
}
