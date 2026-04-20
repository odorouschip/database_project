import type { TeamId, Player } from '../types';

interface Props {
  winningTeam: TeamId;
  players: [Player, Player, Player, Player];
  finalScores: { A: number; B: number };
  onRestart: () => void;
}

export function GameOverScreen({ winningTeam, players, finalScores, onRestart }: Props) {
  const winners = players.filter(p => p.teamId === winningTeam);

  return (
    <div className="screen game-over-screen">
      <div className="game-over-inner">
        <div className="game-over-label">Game Over</div>
        <h1 className="game-over-winner">Team {winningTeam} Wins</h1>
        <div className="game-over-players">
          {winners.map(p => <span key={p.index} className="winner-name">{p.name}</span>)}
        </div>

        <div className="final-scores">
          <div className={`final-score-card ${winningTeam === 'A' ? 'final-winner' : ''}`}>
            <div className="final-team">Team A</div>
            <div className="final-score-names">{players.filter(p => p.teamId === 'A').map(p => p.name).join(' & ')}</div>
            <div className="final-score-total">{finalScores.A}</div>
          </div>
          <div className="final-vs">vs</div>
          <div className={`final-score-card ${winningTeam === 'B' ? 'final-winner' : ''}`}>
            <div className="final-team">Team B</div>
            <div className="final-score-names">{players.filter(p => p.teamId === 'B').map(p => p.name).join(' & ')}</div>
            <div className="final-score-total">{finalScores.B}</div>
          </div>
        </div>

        <button className="btn-primary btn-large" onClick={onRestart}>
          Play Again
        </button>
      </div>
    </div>
  );
}
