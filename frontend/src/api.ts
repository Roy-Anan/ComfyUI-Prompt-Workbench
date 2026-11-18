// Same-origin API client for the local Web runtime.
//
// The frontend is served by FastAPI from the same origin as the API, so all
// requests use relative paths. On first load the client calls /api/bootstrap
// to exchange the local bootstrap token for an HttpOnly session ticket and a
// CSRF token; the ticket cookie is attached automatically by the browser.

type BootstrapResponse = {
  ok: boolean;
  app: string;
  version: string;
  csrf: string;
};

let csrfToken: string | null = null;
let bootstrapPromise: Promise<void> | null = null;

async function bootstrap(): Promise<void> {
  const response = await fetch("/api/bootstrap", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`bootstrap ${response.status}: ${detail}`);
  }

  const body = (await response.json()) as BootstrapResponse;
  csrfToken = body.csrf;
}

async function ensureSession(): Promise<void> {
  if (csrfToken) return;

  if (!bootstrapPromise) {
    bootstrapPromise = bootstrap().finally(() => {
      bootstrapPromise = null;
    });
  }

  await bootstrapPromise;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  await ensureSession();

  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  if (method !== "GET" && csrfToken) {
    headers["X-Workbench-CSRF"] = csrfToken;
  }

  const response = await fetch(path, { ...init, method, headers });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }

  return response.json() as Promise<T>;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(
  path: string,
  body: unknown,
): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function apiDelete<T>(
  path: string,
  body: unknown,
): Promise<T> {
  return request<T>(path, {
    method: "DELETE",
    body: JSON.stringify(body),
  });
}
