import type { Middleware } from "openapi-fetch";

export const QUERY_SUFFIX = "::QUERY";

export const queryMethod: Middleware = {
  async onRequest({ request }) {
    const url = new URL(request.url);
    if (!url.pathname.endsWith(QUERY_SUFFIX)) return undefined;
    url.pathname = url.pathname.slice(0, -QUERY_SUFFIX.length);
    return new Request(url, {
      method: "QUERY",
      headers: request.headers,
      body: await request.clone().arrayBuffer(),
      credentials: request.credentials,
      signal: request.signal,
    });
  },
};
