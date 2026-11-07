const configuredApiUrl = (import.meta as any).env?.VITE_API_URL as string | undefined;

export const API = (configuredApiUrl ?? "").replace(/\/+$/, "");
