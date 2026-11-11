export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Chưa có dữ liệu';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Thời điểm không hợp lệ' : date.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
}

/** Preserve the device's local UTC offset required by the session API contract. */
export function localDateTimeWithOffset(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error('Thời gian không hợp lệ.');
  const minutes = -date.getTimezoneOffset();
  const sign = minutes >= 0 ? '+' : '-';
  const hours = String(Math.floor(Math.abs(minutes) / 60)).padStart(2, '0');
  const rest = String(Math.abs(minutes) % 60).padStart(2, '0');
  return `${value.length === 16 ? `${value}:00` : value}${sign}${hours}:${rest}`;
}
