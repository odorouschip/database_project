import { useState, useEffect } from 'react';
import type { Tile, Player, AttackState, PlayerBoardRecord } from '../types';
import { TileCard, TILE_KANJI, TILE_NAMES } from './TileCard';
import type { TileState } from './TileCard';

function BoardTile({ tile, dim, live }: { tile: Tile; dim: boolean; live?: boolean }) {
  return (
    <div className={`board-tile ${live ? 'board-tile-live' : ''} ${dim ? 'board-tile-dim' : ''}`}>
      <span className="btile-kanji">{TILE_KANJI[tile.kind]}</span>
      <span className="btile-pts">{tile.pointValue}</span>
    </div>
  );
}

function EmptySlot() {
  return <div className="board-slot-empty" />;
}

type AttackSel = { mode: 'attack'; shogunId: number | null; attackId: number | null };
type DefenseSel = { mode: 'defense'; defenseId: number | null; newAttackId: number | null };
type TileSel = AttackSel | DefenseSel;

interface Props {
  currentPlayer: Player;
  hand: Tile[];
  currentAttack: AttackState | null;
  teamScores: { A: number; B: number };
  players: [Player, Player, Player, Player];
  hands: Record<number, Tile[]>;
  boardHistory: Record<number, PlayerBoardRecord>;
  roundNumber: number;
  legalDefenders: Tile[];
  onAttack: (shogunTileId: number, attackTileId: number) => void;
  onDefend: (defenseTileId: number, newAttackTileId: number) => void;
  onPass: () => void;
}

export function PlayerTurnScreen({
  currentPlayer, hand, currentAttack, teamScores,
  players, hands, boardHistory, roundNumber, legalDefenders, onAttack, onDefend, onPass,
}: Props) {
  const isAttackMode = currentAttack === null;
  const [sel, setSel] = useState<TileSel>(
    isAttackMode
      ? { mode: 'attack', shogunId: null, attackId: null }
      : { mode: 'defense', defenseId: null, newAttackId: null }
  );

  const handleTileClick = (tileId: number) => {
    if (sel.mode === 'attack') {
      if (tileId === sel.shogunId) { setSel({ ...sel, shogunId: null }); return; }
      if (tileId === sel.attackId) { setSel({ ...sel, attackId: null }); return; }
      if (sel.shogunId === null) { setSel({ ...sel, shogunId: tileId }); return; }
      if (sel.attackId === null) { setSel({ ...sel, attackId: tileId }); return; }
    } else {
      if (sel.defenseId === null) {
        const isLegal = legalDefenders.some(t => t.id === tileId);
        if (!isLegal) return;
        setSel({ ...sel, defenseId: tileId });
        return;
      }
      if (tileId === sel.defenseId) { setSel({ ...sel, defenseId: null, newAttackId: null }); return; }
      if (tileId === sel.newAttackId) { setSel({ ...sel, newAttackId: null }); return; }
      setSel({ ...sel, newAttackId: tileId });
    }
  };

  const getTileState = (tile: Tile): TileState => {
    if (sel.mode === 'attack') {
      if (tile.id === sel.shogunId) return 'shogun-selected';
      if (tile.id === sel.attackId) return 'attack-selected';
      return 'unselected';
    } else {
      if (tile.id === sel.defenseId) return 'defense-selected';
      if (tile.id === sel.newAttackId) return 'new-attack-selected';
      if (sel.defenseId === null) {
        return legalDefenders.some(t => t.id === tile.id) ? 'legal-defender' : 'illegal';
      }
      return 'unselected';
    }
  };

  const canConfirmAttack = sel.mode === 'attack' && sel.shogunId !== null && sel.attackId !== null;
  const canConfirmDefense = sel.mode === 'defense' && sel.defenseId !== null && sel.newAttackId !== null;
  const mustPassOnly = !isAttackMode && legalDefenders.length === 0;

  const handleConfirm = () => {
    if (canConfirmAttack && sel.mode === 'attack') onAttack(sel.shogunId!, sel.attackId!);
    else if (canConfirmDefense && sel.mode === 'defense') onDefend(sel.defenseId!, sel.newAttackId!);
  };

  return (
    <div className="screen player-turn-screen">
      <div className="turn-header">
        <div className="round-badge">Round {roundNumber}</div>
        <div className="scores-bar">
          <span className="score-team score-a">{teamScores.A}</span>
          <span className="score-sep">/</span>
          <span className="score-team score-b">{teamScores.B}</span>
          <span className="score-target">First to 150</span>
        </div>
      </div>

      <div className="public-board">
        {currentAttack && (
          <div className="board-status-bar">
            <span className="board-status-attacker">
              ⚔ {players[currentAttack.attackerIndex]?.name} attacking
            </span>
            <span className="board-status-tile">
              {TILE_KANJI[currentAttack.attackTile.kind]} {TILE_NAMES[currentAttack.attackTile.kind]} ({currentAttack.attackTile.pointValue}pt)
            </span>
            {currentAttack.consecutivePasses > 0 && (
              <span className="pass-count">{currentAttack.consecutivePasses}/3 passes</span>
            )}
          </div>
        )}

        <div className="board-grid">
          {players.map(p => {
            const record = boardHistory[p.index] ?? { attackTiles: [], defenseTiles: [] };
            const tileCount = hands[p.index]?.length ?? 0;
            const isAttacker = currentAttack?.attackerIndex === p.index;
            const isCurrentTurn = p.index === currentPlayer.index;
            const isPartner = Math.abs(p.index - currentPlayer.index) === 2;

            return (
              <div
                key={p.index}
                className={[
                  'board-player',
                  isAttacker ? 'board-player-attacker' : '',
                  isCurrentTurn ? 'board-player-active' : '',
                  isPartner ? 'board-player-partner' : '',
                ].filter(Boolean).join(' ')}
              >
                <div className="board-player-header">
                  <span className="board-player-name">{p.name}</span>
                  {isCurrentTurn && <span className="board-turn-badge">Your turn</span>}
                  <span className={`board-player-team team-${p.teamId.toLowerCase()}`}>
                    {p.teamId}
                  </span>
                  <span className="board-tile-count">{tileCount} left</span>
                  {isAttacker && !isCurrentTurn && <span className="board-attacker-badge">Attacker</span>}
                </div>

                <div className="board-row">
                  <div className="board-row-label">受け</div>
                  <div className="board-slots">
                    {Array.from({ length: 4 }).map((_, i) => {
                      const tile = record.defenseTiles[i];
                      return tile
                        ? <BoardTile key={i} tile={tile} dim={false} />
                        : <EmptySlot key={i} />;
                    })}
                  </div>
                </div>

                <div className="board-row">
                  <div className="board-row-label">攻め</div>
                  <div className="board-slots">
                    {Array.from({ length: 4 }).map((_, i) => {
                      const tile = record.attackTiles[i];
                      const isLiveAttack = isAttacker && i === record.attackTiles.length - 1 && currentAttack !== null;
                      return tile
                        ? <BoardTile key={i} tile={tile} dim={false} live={isLiveAttack} />
                        : <EmptySlot key={i} />;
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="hand-section">
        <div className="hand-header">
          <span className="hand-player-name">{currentPlayer.name}</span>
          <span className={`hand-team-badge team-${currentPlayer.teamId.toLowerCase()}`}>{currentPlayer.teamId}</span>
          <span className="hand-count">{hand.length} tiles</span>
        </div>

        {mustPassOnly ? (
          <>
          <div className="action-hint">
            You have no defense. You must pass.
          </div>
            <div className="hand-tiles">
              {hand.map(tile => (
                <TileCard
                  key={tile.id}
                  tile={tile}
                  tileState={getTileState(tile)}
                  onClick={() => handleTileClick(tile.id)}
                />
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="action-hint">
              {isAttackMode
                ? sel.mode === 'attack' && sel.shogunId === null
                  ? 'Select your hidden tile (played face-down)'
                  : sel.mode === 'attack' && sel.attackId === null
                    ? 'Select your attack tile (played face-up)'
                    : 'Confirm your attack'
                : sel.mode === 'defense' && sel.defenseId === null
                  ? 'Select a tile to defend with'
                  : sel.mode === 'defense' && sel.newAttackId === null
                    ? 'Select your new attack tile'
                    : 'Confirm your defense'
              }
            </div>
            <div className="hand-tiles">
              {hand.map(tile => (
                <TileCard
                  key={tile.id}
                  tile={tile}
                  tileState={getTileState(tile)}
                  onClick={() => handleTileClick(tile.id)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="actions-bar">
        {mustPassOnly ? (
          <button className="btn-pass" onClick={onPass}>Pass</button>
        ) : (
          <>
            {!isAttackMode && (
              <button className="btn-pass" onClick={onPass}>Pass</button>
            )}
            <button
              className="btn-primary"
              disabled={isAttackMode ? !canConfirmAttack : !canConfirmDefense}
              onClick={handleConfirm}
            >
              {'Play'}
              {hand.length === 2 && ' (Last Tiles)'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
