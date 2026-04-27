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

export interface PollResult {
  moves: RemoteMove[];
  currentRound: number;
}

/**
 * Poll the server for moves with move_id > sinceMoveId, plus the server's current round.
 * Own POSTs are filtered out of the moves list.
 */
export async function pollMatchState(sinceMoveId: number): Promise<PollResult> {
  const gid = getEmbeddedGameId();
  if (gid == null) return { moves: [], currentRound: 1 };

  try {
    const res = await fetch(
      `/api/match/${gid}/moves?since=${sinceMoveId}`,
      { credentials: 'same-origin' },
    );
    if (!res.ok) return { moves: [], currentRound: 1 };
    const data = (await res.json()) as { moves?: RemoteMove[]; current_round?: number };
    const moves = Array.isArray(data.moves)
      ? data.moves.filter(m => !isOwnMove(m.move_id))
      : [];
    const currentRound = typeof data.current_round === 'number' ? data.current_round : 1;
    return { moves, currentRound };
  } catch {
    return { moves: [], currentRound: 1 };
  }
}

/** POST a round-advance signal to the server. Returns the new server-side current_round. */
export async function postRoundAdvance(fromRound: number): Promise<number | null> {
  const gid = getEmbeddedGameId();
  if (gid == null) return null;

  try {
    const res = await fetch(`/api/match/${gid}/round/advance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ from_round: fromRound }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { current_round?: number };
    return typeof data.current_round === 'number' ? data.current_round : null;
  } catch {
    return null;
  }
}
