/**
 * When the Vite app is loaded inside /play/<id>, Flask adds ?game_id=... to the iframe URL
 * so we can POST the final result to the server and unlock matchmaking.
 */
export function getEmbeddedGameId(): number | null {
  if (typeof window === 'undefined') return null;
  const raw = new URLSearchParams(window.location.search).get('game_id');
  if (raw == null) return null;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}
