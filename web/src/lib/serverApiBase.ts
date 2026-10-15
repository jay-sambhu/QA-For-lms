// Backend origin for server-side fetches (server components, sitemap). Read at runtime.
// Accepts values without a scheme (e.g. Render's `hostport` = "ai-qa-api:10000").
export function serverApiBase(): string {
  const raw = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").trim();
  return (/^https?:\/\//.test(raw) ? raw : `http://${raw}`).replace(/\/+$/, "");
}
