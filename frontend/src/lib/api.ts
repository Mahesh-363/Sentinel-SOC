const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

export async function fetchApi<T = any>(
  endpoint: string,
  options: RequestInit = {},
  orgId?: string
): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("sentinel_token") : null;
  const activeOrg = orgId || (typeof window !== "undefined" ? localStorage.getItem("sentinel_active_org") : null);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (activeOrg) {
    headers["X-Organization-Id"] = activeOrg;
  }

  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const res = await fetch(url, {
    cache: "no-store",
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
    } catch {
      errorDetail = await res.text();
    }
    const error = new Error(errorDetail);
    (error as any).status = res.status;
    (error as any).endpoint = endpoint;
    throw error;
  }

  return res.json();
}
