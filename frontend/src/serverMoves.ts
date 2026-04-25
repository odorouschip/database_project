import { getEmbeddedGameId } from './embeddedGame';
import type { PlayerIndex } from './types';
import type { TileKind } from './types';

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
      if (res.ok) return;
      const data = (await res.json().catch(() => ({}))) as { message?: string };
      console.warn('serverMoves: move not saved', res.status, data.message ?? res.statusText);
    })
    .catch((err) => {
      console.warn('serverMoves: network error while recording', err);
    });
}
