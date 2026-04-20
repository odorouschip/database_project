import type { SpecialPawnTrigger, Player, PlayerIndex } from '../types';

interface Props {
  trigger: SpecialPawnTrigger;
  players: [Player, Player, Player, Player];
  pawn5PendingPartner: { triggeringPlayer: PlayerIndex; partnerIndex: PlayerIndex } | null;
  currentViewerIndex: PlayerIndex;
  onAutoWin: () => void;
  onPawn5Reveal: () => void;
  onPawn5PartnerChoice: (choice: 'play_normal' | 'redeal') => void;
}

const TILE_NAMES: Record<string, string> = {
  king: 'King', rook: 'Rook', bishop: 'Bishop', gold: 'Gold',
  silver: 'Silver', knight: 'Knight', lance: 'Lance', pawn: 'Pawn',
};

export function SpecialPawnScreen({
  trigger, players, pawn5PendingPartner, currentViewerIndex,
  onAutoWin, onPawn5Reveal, onPawn5PartnerChoice,
}: Props) {
  if (trigger.type === 'none') return null;

  const triggerPlayer = players[(trigger as { playerIndex: PlayerIndex }).playerIndex]!;

  if (trigger.type === 'pawn8') {
    return (
      <div className="screen special-pawn-screen">
        <div className="special-inner">
          <div className="special-badge pawn-badge">8 Pawns!</div>
          <h2 className="special-title">{triggerPlayer.name} has 8 Pawns</h2>
          <p className="special-desc">Instant round win! <strong>100 points</strong> for Team {triggerPlayer.teamId}.</p>
          <button className="btn-primary btn-large" onClick={onAutoWin}>Claim Points</button>
        </div>
      </div>
    );
  }

  if (trigger.type === 'pawn7') {
    const score = 2 * trigger.nonPawnTile.pointValue;
    return (
      <div className="screen special-pawn-screen">
        <div className="special-inner">
          <div className="special-badge pawn-badge">7 Pawns!</div>
          <h2 className="special-title">{triggerPlayer.name} has 7 Pawns</h2>
          <p className="special-desc">
            Non-pawn tile: <strong>{TILE_NAMES[trigger.nonPawnTile.kind]}</strong> ({trigger.nonPawnTile.pointValue} pts × 2)
          </p>
          <p className="special-score">= <strong>{score} points</strong> for Team {triggerPlayer.teamId}</p>
          <button className="btn-primary btn-large" onClick={onAutoWin}>Claim Points</button>
        </div>
      </div>
    );
  }

  if (trigger.type === 'pawn6') {
    const score = trigger.nonPawnTiles[0].pointValue + trigger.nonPawnTiles[1].pointValue;
    return (
      <div className="screen special-pawn-screen">
        <div className="special-inner">
          <div className="special-badge pawn-badge">6 Pawns!</div>
          <h2 className="special-title">{triggerPlayer.name} has 6 Pawns</h2>
          <p className="special-desc">
            Non-pawn tiles: <strong>{TILE_NAMES[trigger.nonPawnTiles[0].kind]}</strong> ({trigger.nonPawnTiles[0].pointValue} pts)
            {' + '}
            <strong>{TILE_NAMES[trigger.nonPawnTiles[1].kind]}</strong> ({trigger.nonPawnTiles[1].pointValue} pts)
          </p>
          <p className="special-score">= <strong>{score} points</strong> for Team {triggerPlayer.teamId}</p>
          <button className="btn-primary btn-large" onClick={onAutoWin}>Claim Points</button>
        </div>
      </div>
    );
  }

  if (trigger.type === 'pawn5') {
    // Phase 2: partner is deciding
    if (pawn5PendingPartner) {
      const partnerPlayer = players[pawn5PendingPartner.partnerIndex]!;
      const isViewerThePartner = currentViewerIndex === pawn5PendingPartner.partnerIndex;
      if (!isViewerThePartner) return null;

      return (
        <div className="screen special-pawn-screen">
          <div className="special-inner">
            <div className="special-badge pawn5-badge">5 Pawns</div>
            <h2 className="special-title">{triggerPlayer.name} revealed 5 Pawns</h2>
            <p className="special-desc">
              {partnerPlayer.name}, as their partner, you must decide how to proceed.
            </p>
            <div className="pawn5-choices">
              <button className="btn-choice" onClick={() => onPawn5PartnerChoice('play_normal')}>
                <span className="choice-title">Play Normally</span>
                <span className="choice-desc">Continue the round as usual</span>
              </button>
              <button className="btn-choice btn-choice-alt" onClick={() => onPawn5PartnerChoice('redeal')}>
                <span className="choice-title">Redeal</span>
                <span className="choice-desc">Shuffle and deal new hands</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    // Phase 1: triggerring player just revealed -> needs to be acknowledged before partner checks
    return (
      <div className="screen special-pawn-screen">
        <div className="special-inner">
          <div className="special-badge pawn5-badge">5 Pawns</div>
          <h2 className="special-title">{triggerPlayer.name} has 5 Pawns</h2>
          <p className="special-desc">Checking if their partner also has 5 Pawns...</p>
          <button className="btn-primary btn-large" onClick={onPawn5Reveal}>
            Check Partner
          </button>
        </div>
      </div>
    );
  }

  return null;
}
