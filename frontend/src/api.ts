export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? body.detail
        : `Request failed (${response.status})`;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  return response.json() as Promise<T>;
}
export function post<T>(path: string, body: unknown): Promise<T> {
  return api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export const pct = (v: number | null | undefined, digits = 1) =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;
export const num = (v: number | null | undefined, digits = 2) =>
  v == null ? "—" : v.toFixed(digits);
export const label = (s: string) =>
  s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
