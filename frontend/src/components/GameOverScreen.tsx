import type { TeamId, Player } from '../types';

interface Props {
  winningTeam: TeamId;
  players: [Player, Player, Player, Player];
  finalScores: { A: number; B: number };
  onRestart: () => void;
  /** When true (embedded play page), show saving state */
  savingResult?: boolean;
  /** After server has the result; play again enabled when embedded */
  matchSaved?: boolean;
  onBackToLobby?: () => void;
}

export function GameOverScreen({
  winningTeam,
  players,
  finalScores,
  onRestart,
  savingResult = false,
  matchSaved = true,
  onBackToLobby,
}: Props) {
  const winners = players.filter(p => p.teamId === winningTeam);
  const embedded = Boolean(onBackToLobby);
  const playLocked = embedded && (savingResult || !matchSaved);

  return (
    <div className="screen game-over-screen">
      <div className="game-over-inner">
        <div className="game-over-label">Game Over</div>
        <h1 className="game-over-winner">Team {winningTeam} Wins</h1>
        {embedded && savingResult && (
          <p className="game-over-saving">Saving to match history…</p>
        )}

        <div className="game-over-players">
          {winners.map(p => (
            <span key={p.index} className="winner-name">
              {p.name}
            </span>
          ))}
        </div>

        <div className="final-scores">
          <div className={`final-score-card ${winningTeam === 'A' ? 'final-winner' : ''}`}>
            <div className="final-team">Team A</div>
            <div className="final-score-names">
              {players
                .filter(p => p.teamId === 'A')
                .map(p => p.name)
                .join(' & ')}
            </div>
            <div className="final-score-total">{finalScores.A}</div>
          </div>
          <div className="final-vs">vs</div>
          <div className={`final-score-card ${winningTeam === 'B' ? 'final-winner' : ''}`}>
            <div className="final-team">Team B</div>
            <div className="final-score-names">
              {players
                .filter(p => p.teamId === 'B')
                .map(p => p.name)
                .join(' & ')}
            </div>
            <div className="final-score-total">{finalScores.B}</div>
          </div>
        </div>

        <div className="game-over-actions">
          {onBackToLobby && (
            <button
              type="button"
              className="btn-primary btn-large"
              disabled={embedded && (savingResult || !matchSaved)}
              onClick={onBackToLobby}
            >
              {embedded && (savingResult || !matchSaved) ? 'Saving…' : 'Back to lobby'}
            </button>
          )}
          <button
            type="button"
            className={onBackToLobby ? 'btn-secondary btn-large' : 'btn-primary btn-large'}
            disabled={playLocked}
            onClick={onRestart}
            title={playLocked ? 'Wait for the result to be saved' : undefined}
          >
            Play again (same players)
          </button>
        </div>
        {embedded && (
          <p className="game-over-hint">
            Your result is saved automatically. Use Back to lobby when you are done, or play again for a new match
            with the same group (opens a new table in your history when you finish the next game).
          </p>
        )}
      </div>
    </div>
  );
}
