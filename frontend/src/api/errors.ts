export function getApiError(err: unknown, fallback = "Ошибка"): string {
  if (typeof err === "object" && err !== null) {
    const e = err as { response?: { data?: { detail?: unknown } } };
    if (typeof e.response?.data?.detail === "string") {
      return e.response.data.detail;
    }
  }
  return fallback;
}
