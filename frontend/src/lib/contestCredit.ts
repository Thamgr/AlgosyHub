export const MAX_CREDIT_THRESHOLD = 2_147_483_647;

export function parseCreditThreshold(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return undefined;
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed > 0 && parsed <= MAX_CREDIT_THRESHOLD ? parsed : undefined;
}
