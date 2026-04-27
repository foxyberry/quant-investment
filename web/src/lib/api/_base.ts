export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      const raw = body.detail ?? body.message ?? '';
      detail = typeof raw === 'string' ? raw : JSON.stringify(raw);
    } catch { /* ignore parse errors */ }
    throw new Error(detail || `API Error: ${response.status}`);
  }

  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return response.json();
}
