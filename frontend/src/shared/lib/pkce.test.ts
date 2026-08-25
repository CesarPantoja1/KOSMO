import { describe, expect, it } from 'vitest';
import { generateCodeVerifier, generateCodeChallenge } from './pkce';

import { webcrypto } from 'node:crypto';
if (!globalThis.window) {
    // @ts-expect-error Polyfill
    globalThis.window = {};
}
if (!globalThis.window.crypto) {
    // @ts-expect-error Polyfill
    globalThis.window.crypto = webcrypto;
}

describe('PKCE Lib', () => {
    describe('generateCodeVerifier', () => {
        it('should generate a valid code verifier string', () => {
            const verifier = generateCodeVerifier();
            expect(typeof verifier).toBe('string');
            expect(verifier.length).toBe(56);
            expect(/^[0-9a-f]+$/i.test(verifier)).toBe(true);
        });

        it('should generate random values', () => {
            const verifier1 = generateCodeVerifier();
            const verifier2 = generateCodeVerifier();
            expect(verifier1).not.toBe(verifier2);
        });
    });

    describe('generateCodeChallenge', () => {
        it('should generate a valid S256 code challenge from a verifier', async () => {
            const testVerifier = 'dBjftJeZ4CVK-mJq2OEpEO83wFvO_I-9zU4C1YQ3Lkw';
            const challenge = await generateCodeChallenge(testVerifier);
            expect(typeof challenge).toBe('string');
            expect(challenge).toBe('ugvfXSrJyC5JWeNAbYaH8r8I8tc5C-j-em_0l0qjcJI');
        });

        it('should be Base64URL encoded (no =, +, /)', async () => {
            const verifier = generateCodeVerifier();
            const challenge = await generateCodeChallenge(verifier);
            expect(challenge).not.toContain('=');
            expect(challenge).not.toContain('+');
            expect(challenge).not.toContain('/');
            expect(/^[a-zA-Z0-9_-]+$/.test(challenge)).toBe(true);
        });
    });
});

