import { getEmbeddedGameId } from './embeddedGame';

export interface GamePlayer {
  seat: number;
  username: string;
}

export interface GameInfo {
  players: [GamePlayer, GamePlayer, GamePlayer, GamePlayer];
  mySeat: number;
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
    };
    if (!Array.isArray(data.players) || data.players.length !== 4) return null;
    if (typeof data.my_seat !== 'number') return null;

    const sorted = [...data.players].sort((a, b) => a.seat - b.seat) as
      [GamePlayer, GamePlayer, GamePlayer, GamePlayer];

    return { players: sorted, mySeat: data.my_seat };
  } catch {
    return null;
  }
}
