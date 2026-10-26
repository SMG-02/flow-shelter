
const BASE = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

let token: string | null = null;

export const setToken = (t: string | null) => {
  token = t;
};

export async function api<T = unknown>(
  path: string,
  options: { method?: string; body?: unknown } = {}
): Promise<T> {
  const { method = "GET", body } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let res: Response;

  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `Cannot reach the backend at ${BASE}. Check that the API is running.`
    );
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : typeof data?.detail?.message === "string"
          ? data.detail.message
          : `Request failed (${res.status})`;

    const error = new Error(detail) as Error & {
      status?: number;
      data?: unknown;
    };

    error.status = res.status;
    error.data = data;
    throw error;
  }

  return data as T;
}