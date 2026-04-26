import { getEmbeddedGameId } from './embeddedGame';
import type { PlayerIndex } from './types';
import type { TileKind } from './types';

// Move ids this client has POSTed itself, so the polling loop can ignore its own echoes.
const ownMoveIds = new Set<number>();

export function isOwnMove(moveId: number): boolean {
  return ownMoveIds.has(moveId);
}

/**
 * Log one turn to the server for match replay. No-op if not in an embedded /play/ session.
 */
export function tryRecordMove(options: {
  roundNumber: number;
  playerIndex: PlayerIndex;
  tileKinds: TileKind[];
}): void {
  const gid = getEmbeddedGameId();
  if (gid == null) return;

  const body = {
    round_number: options.roundNumber,
    seat_position: options.playerIndex + 1,
    tile_kinds: options.tileKinds,
  };

  void fetch(`/api/match/${gid}/moves`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  })
    .then(async (res) => {
      const data = (await res.json().catch(() => ({}))) as { message?: string; move_id?: number };
      if (!res.ok) {
        console.warn('serverMoves: move not saved', res.status, data.message ?? res.statusText);
        return;
      }
      if (typeof data.move_id === 'number') ownMoveIds.add(data.move_id);
    })
    .catch((err) => {
      console.warn('serverMoves: network error while recording', err);
    });
}
