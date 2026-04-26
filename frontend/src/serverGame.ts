import { getEmbeddedGameId } from './embeddedGame';

export interface GamePlayer {
  seat: number;
  username: string;
}

export interface GameInfo {
  players: [GamePlayer, GamePlayer, GamePlayer, GamePlayer];
  mySeat: number;
  dealSeed: number | null;
}

/**
 * Load the 4 players + caller's seat for the embedded /play/<id> game.
 * Returns null if not in an embedded session or if the call fails.
 */
export async function loadGameInfo(): Promise<GameInfo | null> {
  const gid = getEmbeddedGameId();
  if (gid == null) return null;

  try {
    const res = await fetch(`/api/game/${gid}/players`, {
      credentials: 'same-origin',
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      players?: GamePlayer[];
      my_seat?: number;
      deal_seed?: number | null;
    };
    if (!Array.isArray(data.players) || data.players.length !== 4) return null;
    if (typeof data.my_seat !== 'number') return null;

    const sorted = [...data.players].sort((a, b) => a.seat - b.seat) as
      [GamePlayer, GamePlayer, GamePlayer, GamePlayer];

    const dealSeed = typeof data.deal_seed === 'number' ? data.deal_seed : null;

    return { players: sorted, mySeat: data.my_seat, dealSeed };
  } catch {
    return null;
  }
}
