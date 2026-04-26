import { getEmbeddedGameId } from './embeddedGame';
import { isOwnMove } from './serverMoves';
import type { TileKind } from './types';

export interface RemoteMove {
  move_id: number;
  order_played: number;
  round_number: number;
  seat_position: number;
  tile_kinds: TileKind[];
}

/**
 * Poll the server for moves with move_id > sinceMoveId.
 * Returns moves played by other clients (own POSTs are filtered out).
 */
export async function fetchNewMoves(sinceMoveId: number): Promise<RemoteMove[]> {
  const gid = getEmbeddedGameId();
  if (gid == null) return [];

  try {
    const res = await fetch(
      `/api/match/${gid}/moves?since=${sinceMoveId}`,
      { credentials: 'same-origin' },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as { moves?: RemoteMove[] };
    if (!Array.isArray(data.moves)) return [];
    return data.moves.filter(m => !isOwnMove(m.move_id));
  } catch {
    return [];
  }
}
