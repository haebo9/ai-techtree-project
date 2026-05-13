export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

export function apiPath(path: string): string {
  const normalizedBase = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}
