export function generateCodeVerifier(): string {
	const array = new Uint32Array(28); // 28 * 4 bytes = 112 bytes
	window.crypto.getRandomValues(array);
	return Array.from(array, (dec) => ('0' + dec.toString(16)).slice(-2)).join('');
}

function base64UrlEncode(buffer: ArrayBuffer): string {
	const bytes = new Uint8Array(buffer);
	let str = '';
	for (let i = 0; i < bytes.byteLength; i++) {
		str += String.fromCharCode(bytes[i]);
	}
	const base64 = btoa(str);
	return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export async function generateCodeChallenge(verifier: string): Promise<string> {
	const encoder = new TextEncoder();
	const data = encoder.encode(verifier);
	const digest = await window.crypto.subtle.digest('SHA-256', data);
	return base64UrlEncode(digest);
}
