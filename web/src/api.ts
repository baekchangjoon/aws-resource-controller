import type { AddressResponse, ListMessagesResponse } from "./types";

const apiBase = (): string => {
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  return (fromEnv ?? "http://localhost:8000").replace(/\/$/, "");
};

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  const text = await res.text();
  const payload = text ? JSON.parse(text) : {};
  if (!res.ok) {
    throw new Error(`${res.status} ${payload.error ?? "error"}`);
  }
  return payload as T;
}

export const api = {
  createAddress: () => call<AddressResponse>("POST", "/addresses", {}),
  deleteAddress: (addr: string) =>
    call<void>("DELETE", `/addresses/${encodeURIComponent(addr)}`),
  listMessages: (addr: string, after?: string) => {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return call<ListMessagesResponse>(
      "GET",
      `/addresses/${encodeURIComponent(addr)}/messages${qs}`
    );
  },
  presignAttachment: (addr: string, msgId: string, aid: string) =>
    call<{ url: string; expires_in: number }>(
      "GET",
      `/messages/${encodeURIComponent(addr)}/${encodeURIComponent(msgId)}/attach/${encodeURIComponent(aid)}`
    ),
};
