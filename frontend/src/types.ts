export type TileKind = 'king' | 'rook' | 'bishop' | 'gold' | 'silver' | 'knight' | 'lance' | 'pawn';

export interface Tile {
  id: number;
  kind: TileKind;
  pointValue: number;
}

export type PlayerIndex = 0 | 1 | 2 | 3;
export type TeamId = 'A' | 'B';

export interface Player {
  index: PlayerIndex;
  name: string;
  teamId: TeamId;
}

export interface AttackState {
  attackerIndex: PlayerIndex;
  shogunTile: Tile;
  attackTile: Tile;
  consecutivePasses: number;
}

export type SpecialPawnTrigger =
  | { type: 'none' }
  | { type: 'pawn8'; playerIndex: PlayerIndex }
  | { type: 'pawn7'; playerIndex: PlayerIndex; nonPawnTile: Tile }
  | { type: 'pawn6'; playerIndex: PlayerIndex; nonPawnTiles: [Tile, Tile] }
  | { type: 'pawn5'; playerIndex: PlayerIndex };

export interface RoundResult {
  winningTeam: TeamId;
  pointsScored: number;
  reason: 'last_tiles' | 'pawn8' | 'pawn7' | 'pawn6' | 'pawn5_both_partners';
  scoringTile?: Tile;
}

export interface PlayerBoardRecord {
  attackTiles: Tile[];
  defenseTiles: Tile[];
}

export interface RoundState {
  roundNumber: number;
  dealerIndex: PlayerIndex;
  hands: Record<PlayerIndex, Tile[]>;
  currentAttack: AttackState | null;
  currentPlayerIndex: PlayerIndex;
  specialPawnTrigger: SpecialPawnTrigger | null;
  pawn5PendingPartner: { triggeringPlayer: PlayerIndex; partnerIndex: PlayerIndex } | null;
  roundResult: RoundResult | null;
  boardHistory: Record<PlayerIndex, PlayerBoardRecord>;
}

export type ScreenId = 'setup' | 'transition' | 'player_turn' | 'special_pawn' | 'round_over' | 'game_over';

export interface GameState {
  screen: ScreenId;
  players: [Player, Player, Player, Player] | null;
  teamScores: { A: number; B: number };
  round: RoundState | null;
  transition: { nextPlayerIndex: PlayerIndex; afterScreen: 'player_turn' | 'special_pawn' } | null;
}
