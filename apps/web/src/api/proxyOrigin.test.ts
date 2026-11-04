import {expect, it} from 'vitest';
import {proxyOriginHeaders} from '../../proxy-origin';

it('preserves localhost while restoring only the configured public HTTPS origin', () => {
  const trusted = 'https://camera.example.test';
  expect(proxyOriginHeaders('127.0.0.1:5173', 'http://127.0.0.1:5173', trusted)).toEqual({'x-forwarded-proto':'http'});
  expect(proxyOriginHeaders('127.0.0.1:4173', trusted, trusted)).toEqual({host:'camera.example.test','x-forwarded-proto':'https'});
  expect(proxyOriginHeaders('camera.example.test', undefined, trusted)).toEqual({host:'camera.example.test','x-forwarded-proto':'https'});
  expect(proxyOriginHeaders('127.0.0.1:5173', 'https://attacker.test', trusted)).toEqual({'x-forwarded-proto':'http'});
  expect(proxyOriginHeaders('127.0.0.1:5173', trusted)).toEqual({'x-forwarded-proto':'http'});
});

it('rejects public origin configuration containing credentials or paths', () => {
  expect(() => proxyOriginHeaders('', '', 'https://user:secret@example.test')).toThrow();
  expect(() => proxyOriginHeaders('', '', 'https://example.test/path')).toThrow();
});
