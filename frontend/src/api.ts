import { parseEvent, parseSnapshot, type RunEvent } from "./model";
const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
export async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${base}/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    let code = "";
    try {
      const body = await response.json();
      if (
        typeof body.error_code === "string" &&
        /^[a-z0-9_]{1,80}$/i.test(body.error_code)
      )
        code = ` (${body.error_code})`;
    } catch {
      /* Error body is optional. */
    }
    throw Error(
      `API ${response.status}: ${response.status === 404 ? "Run or API endpoint unavailable" : response.statusText}${code}. No fixture was substituted.`,
    );
  }
  const content = response.headers.get("content-type") || "";
  if (!content.includes("application/json"))
    throw Error(
      "API returned non-JSON content. Check API_PROXY_TARGET / VITE_API_URL.",
    );
  return response.json();
}
export const snapshot = async (id: string) =>
  parseSnapshot(await request(`/runs/${encodeURIComponent(id)}`), id);
export function subscribe(
  id: string,
  after: number,
  onEvent: (e: RunEvent) => void,
  onError: (message: string) => void,
) {
  const stream = new EventSource(
    `${base}/api/runs/${encodeURIComponent(id)}/events?after_seq=${after}`,
  );
  stream.onmessage = (message) => {
    try {
      onEvent(parseEvent(JSON.parse(message.data)));
    } catch (e) {
      stream.close();
      onError(e instanceof Error ? e.message : "Invalid stream message");
    }
  };
  stream.onerror = () => {
    stream.close();
    onError(
      "Event stream disconnected. Use Reconnect to restore persisted evidence.",
    );
  };
  return () => stream.close();
}
