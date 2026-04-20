import type { Tile } from '../types';

export type TileState =
  | 'unselected'
  | 'shogun-selected'
  | 'attack-selected'
  | 'defense-selected'
  | 'new-attack-selected'
  | 'legal-defender'
  | 'illegal'
  | 'face-up-display'
  | 'disabled';

export const TILE_KANJI: Record<string, string> = {
  king: '王',
  rook: '飛',
  bishop: '角',
  gold: '金',
  silver: '銀',
  knight: '桂',
  lance: '香',
  pawn: 'し',
};

export const TILE_NAMES: Record<string, string> = {
  king: 'King',
  rook: 'Rook',
  bishop: 'Bishop',
  gold: 'Gold',
  silver: 'Silver',
  knight: 'Knight',
  lance: 'Lance',
  pawn: 'Pawn',
};

interface Props {
  tile: Tile;
  tileState?: TileState;
  onClick?: () => void;
}

export function TileCard({ tile, tileState = 'unselected', onClick }: Props) {
  const isClickable = onClick &&
    tileState !== 'illegal' &&
    tileState !== 'disabled' &&
    tileState !== 'face-up-display';

  return (
    <div className="tile-wrap">
      <button
        className={`tile-card tile-${tileState}`}
        onClick={isClickable ? onClick : undefined}
        disabled={!isClickable}
        aria-label={`${TILE_NAMES[tile.kind]} ${tile.pointValue} points`}
      >
        <span className="tile-kanji">{TILE_KANJI[tile.kind]}</span>
        <span className="tile-name">{TILE_NAMES[tile.kind]}</span>
        <span className="tile-pts">{tile.pointValue}</span>
      </button>
    </div>
  );
}

export function FaceDownTile({ label }: { label?: string }) {
  return (
    <div className="tile-wrap">
      <div className="tile-card tile-face-down" aria-label="Hidden tile">
        <span className="tile-kanji">裏</span>
        {label && <span className="tile-name">{label}</span>}
      </div>
    </div>
  );
}
