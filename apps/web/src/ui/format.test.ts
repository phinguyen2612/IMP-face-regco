import { expect, it, vi } from 'vitest';
import { localDateTimeWithOffset } from './format';

it('preserves the local session time and includes the UTC offset required by the backend', () => {
  const offset = vi.spyOn(Date.prototype, 'getTimezoneOffset').mockReturnValue(-420);
  expect(localDateTimeWithOffset('2026-11-06T08:00')).toBe('2026-11-06T08:00:00+07:00');
  offset.mockReturnValue(300);
  expect(localDateTimeWithOffset('2026-11-06T08:00')).toBe('2026-11-06T08:00:00-05:00');
  offset.mockRestore();
});
