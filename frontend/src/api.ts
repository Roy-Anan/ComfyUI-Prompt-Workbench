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
    const detail = await describeError(response);
    throw new Error(`bootstrap ${response.status}: ${detail}`);
  }

  const body = (await response.json()) as BootstrapResponse;
  csrfToken = body.csrf;
}

async function describeError(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    // Non-JSON body: fall back to the raw response text.
  }
  return text;
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
    const detail = await describeError(response);
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

// Raw binary POST (e.g. restoring a backup ZIP). The body is sent as-is; the
// CSRF header is attached for the cookie session.
export async function apiPostBinary(
  path: string,
  body: Blob | ArrayBuffer,
): Promise<Record<string, unknown>> {
  await ensureSession();
  const headers: Record<string, string> = {};
  if (csrfToken) headers["X-Workbench-CSRF"] = csrfToken;
  const response = await fetch(path, { method: "POST", headers, body });
  if (!response.ok) {
    const detail = await describeError(response);
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

// Read-only binary download (e.g. the local backup ZIP). GET requests carry
// the session cookie automatically and need no CSRF header.
export async function apiGetBlob(path: string): Promise<Blob> {
  await ensureSession();
  const response = await fetch(path, { method: "GET" });
  if (!response.ok) {
    const detail = await describeError(response);
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.blob();
}
