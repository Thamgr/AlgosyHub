export function getApiError(err: unknown, fallback = "Ошибка"): string {
  if (typeof err === "object" && err !== null) {
    const e = err as { response?: { data?: unknown } };
    let data = e.response?.data;
    // HTML endpoints use responseType: "text", including for JSON errors.
    if (typeof data === "string") {
      try { data = JSON.parse(data); } catch { return fallback; }
    }
    if (typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string") {
      return data.detail;
    }
  }
  return fallback;
}
