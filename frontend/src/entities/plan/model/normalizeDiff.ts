export function normalizeDiff(diffBefore: string, diffAfter: string): { before: string; after: string } {
	if (
		diffBefore &&
		diffAfter &&
		diffAfter.startsWith(diffBefore) &&
		diffAfter.length > diffBefore.length
	) {
		return { before: '', after: diffAfter.slice(diffBefore.length).trim() };
	}
	return { before: diffBefore, after: diffAfter };
}
