/** <input type="datetime-local"> works in local wall-clock time; the API wants ISO 8601 with an offset. */

const pad = (n: number) => String(n).padStart(2, '0');

/** A Date as the value of a datetime-local input. */
export function toLocalInput(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** A datetime-local value as an ISO timestamp (UTC), or '' if empty or invalid. */
export function fromLocalInput(value: string): string {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString();
}

/** Tomorrow at the given local hour. */
export function tomorrowAt(hour: number): Date {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(hour, 0, 0, 0);
  return date;
}
