import type { Tile, TileKind, PlayerIndex, TeamId, AttackState, RoundState, RoundResult, SpecialPawnTrigger } from './types';

const TILE_COUNTS: Record<TileKind, number> = {
  king: 2, rook: 2, bishop: 2, gold: 4, silver: 4, knight: 4, lance: 4, pawn: 10,
};

export function getTileValue(kind: TileKind): number {
  switch (kind) {
    case 'king': return 50;
    case 'rook': return 40;
    case 'bishop': return 40;
    case 'gold': return 30;
    case 'silver': return 30;
    case 'knight': return 20;
    case 'lance': return 20;
    case 'pawn': return 10;
  }
}

export function buildDeck(): Tile[] {
  const tiles: Tile[] = [];
  let id = 0;
  for (const [kind, count] of Object.entries(TILE_COUNTS) as [TileKind, number][]) {
    for (let i = 0; i < count; i++) {
      tiles.push({ id: id++, kind, pointValue: getTileValue(kind) });
    }
  }
  return tiles;
}

export function shuffleDeck(deck: Tile[]): Tile[] {
  const arr = [...deck];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j]!, arr[i]!];
  }
  return arr;
}

// Mulberry32: tiny deterministic PRNG that takes a 32-bit seed.
// Same seed → same number sequence on every device.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffleDeckSeeded(deck: Tile[], seed: number): Tile[] {
  const arr = [...deck];
  const rand = mulberry32(seed);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [arr[i], arr[j]] = [arr[j]!, arr[i]!];
  }
  return arr;
}

export function dealHands(deck: Tile[]): Record<PlayerIndex, Tile[]> {
  if (deck.length !== 32) throw new Error(`Expected 32 tiles, got ${deck.length}`);
  return {
    0: deck.slice(0, 8),
    1: deck.slice(8, 16),
    2: deck.slice(16, 24),
    3: deck.slice(24, 32),
  };
}

export function canDefend(attack: Tile, defender: Tile): boolean {
  if (defender.kind === attack.kind) return attack.kind !== 'king';
  if (defender.kind === 'king') {
    return ['rook', 'bishop', 'gold', 'silver', 'knight'].includes(attack.kind);
  }
  return false;
}

export function getLegalDefenders(hand: Tile[], attackTile: Tile): Tile[] {
  return hand.filter(t => canDefend(attackTile, t));
}

export function checkSpecialPawnHands(hands: Record<PlayerIndex, Tile[]>): SpecialPawnTrigger {
  // Check in priority order per player: 8 > 7 > 6 > 5
  const priorities = [8, 7, 6, 5] as const;
  for (const pawnCount of priorities) {
    for (const index of [0, 1, 2, 3] as PlayerIndex[]) {
      const hand = hands[index]!;
      const pawns = hand.filter(t => t.kind === 'pawn');
      if (pawns.length === pawnCount) {
        const nonPawns = hand.filter(t => t.kind !== 'pawn');
        if (pawnCount === 8) return { type: 'pawn8', playerIndex: index };
        if (pawnCount === 7) return { type: 'pawn7', playerIndex: index, nonPawnTile: nonPawns[0]! };
        if (pawnCount === 6) return { type: 'pawn6', playerIndex: index, nonPawnTiles: [nonPawns[0]!, nonPawns[1]!] };
        if (pawnCount === 5) return { type: 'pawn5', playerIndex: index };
      }
    }
  }
  return { type: 'none' };
}

export function computeSpecialPawnScore(trigger: SpecialPawnTrigger): number {
  if (trigger.type === 'pawn8') return 100;
  if (trigger.type === 'pawn7') return 2 * trigger.nonPawnTile.pointValue;
  if (trigger.type === 'pawn6') return trigger.nonPawnTiles[0].pointValue + trigger.nonPawnTiles[1].pointValue;
  return 0;
}

export function checkPawn5Partner(hands: Record<PlayerIndex, Tile[]>, playerIndex: PlayerIndex): boolean {
  const partnerIndex = getPartnerIndex(playerIndex);
  const partnerHand = hands[partnerIndex]!;
  return partnerHand.filter(t => t.kind === 'pawn').length === 5;
}

export function removeTileFromHand(hand: Tile[], tileId: number): Tile[] {
  const index = hand.findIndex(t => t.id === tileId);
  if (index === -1) throw new Error(`Tile id ${tileId} not found in hand`);
  return [...hand.slice(0, index), ...hand.slice(index + 1)];
}

export function nextPlayer(current: PlayerIndex): PlayerIndex {
  return ((current + 1) % 4) as PlayerIndex;
}

export function getPartnerIndex(playerIndex: PlayerIndex): PlayerIndex {
  return ((playerIndex + 2) % 4) as PlayerIndex;
}

export function getTeamId(playerIndex: PlayerIndex): TeamId {
  return playerIndex === 0 || playerIndex === 2 ? 'A' : 'B';
}

export function computeRoundEndResult(playerIndex: PlayerIndex, attack: AttackState): RoundResult {
  return {
    winningTeam: getTeamId(playerIndex),
    pointsScored: attack.attackTile.pointValue,
    reason: 'last_tiles',
    scoringTile: attack.attackTile,
  };
}

export function isGameOver(scores: { A: number; B: number }): boolean {
  return scores.A >= 150 || scores.B >= 150;
}

export function getWinner(scores: { A: number; B: number }): TeamId | null {
  if (scores.A >= 150 && scores.B >= 150) return scores.A >= scores.B ? 'A' : 'B';
  if (scores.A >= 150) return 'A';
  if (scores.B >= 150) return 'B';
  return null;
}

function emptyBoardHistory(): Record<PlayerIndex, import('./types').PlayerBoardRecord> {
  return { 0: { attackTiles: [], defenseTiles: [] }, 1: { attackTiles: [], defenseTiles: [] }, 2: { attackTiles: [], defenseTiles: [] }, 3: { attackTiles: [], defenseTiles: [] } };
}

export function initRound(roundNumber: number, dealerIndex: PlayerIndex, dealSeed?: number | null): RoundState {
  // If a seed is supplied, derive a per-round seed so each round still gets a different shuffle
  // but every client agrees because they all start from the same base seed.
  const deck = (dealSeed != null)
    ? shuffleDeckSeeded(buildDeck(), (dealSeed ^ (roundNumber * 0x9e3779b1)) >>> 0)
    : shuffleDeck(buildDeck());
  const hands = dealHands(deck);
  const specialPawnTrigger = checkSpecialPawnHands(hands);

  return {
    roundNumber,
    dealerIndex,
    hands,
    currentAttack: null,
    currentPlayerIndex: dealerIndex,
    specialPawnTrigger: specialPawnTrigger.type === 'none' ? null : specialPawnTrigger,
    pawn5PendingPartner: null,
    roundResult: null,
    boardHistory: emptyBoardHistory(),
  };
}
