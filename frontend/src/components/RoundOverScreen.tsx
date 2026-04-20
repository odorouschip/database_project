import type { RoundResult, Player } from '../types';

interface Props {
  roundResult: RoundResult;
  teamScores: { A: number; B: number };
  players: [Player, Player, Player, Player];
  roundNumber: number;
  onNextRound: () => void;
}

const REASON_LABELS: Record<RoundResult['reason'], string> = {
  last_tiles: 'Played last tiles',
  pawn8: '8 Pawns',
  pawn7: '7 Pawns',
  pawn6: '6 Pawns',
  pawn5_both_partners: '5 Pawns (both partners)',
};

export function RoundOverScreen({ roundResult, teamScores, players, roundNumber, onNextRound }: Props) {
  const teamAPlayers = players.filter(p => p.teamId === 'A').map(p => p.name).join(' & ');
  const teamBPlayers = players.filter(p => p.teamId === 'B').map(p => p.name).join(' & ');

  const isTeamAWinner = roundResult.winningTeam === 'A';
  const gameOver = teamScores.A >= 150 || teamScores.B >= 150;

  return (
    <div className="screen round-over-screen">
      <div className="round-over-inner">
        <div className="round-badge">Round {roundNumber}</div>
        <h2 className="round-over-title">Round Over</h2>

        <div className={`winner-banner team-banner-${roundResult.winningTeam.toLowerCase()}`}>
          <div className="winner-team-label">Team {roundResult.winningTeam} wins the round</div>
          <div className="winner-points">+{roundResult.pointsScored} pts</div>
          {roundResult.scoringTile && (
            <div className="scoring-tile-label">
              on {roundResult.scoringTile.kind} ({roundResult.scoringTile.pointValue} pts)
            </div>
          )}
          <div className="round-reason">{REASON_LABELS[roundResult.reason]}</div>
        </div>

        <div className="scores-panel">
          <div className={`score-card ${isTeamAWinner ? 'score-card-winner' : ''}`}>
            <div className="score-card-team">Team A</div>
            <div className="score-card-players">{teamAPlayers}</div>
            <div className="score-card-total">{teamScores.A}</div>
            <div className="score-card-bar">
              <div className="score-bar-fill" style={{ width: `${Math.min(100, (teamScores.A / 150) * 100)}%` }} />
            </div>
          </div>
          <div className="score-card-sep">vs</div>
          <div className={`score-card ${!isTeamAWinner ? 'score-card-winner' : ''}`}>
            <div className="score-card-team">Team B</div>
            <div className="score-card-players">{teamBPlayers}</div>
            <div className="score-card-total">{teamScores.B}</div>
            <div className="score-card-bar">
              <div className="score-bar-fill" style={{ width: `${Math.min(100, (teamScores.B / 150) * 100)}%` }} />
            </div>
          </div>
        </div>

        <button className="btn-primary btn-large" onClick={onNextRound}>
          {gameOver ? 'See Final Result' : 'Next Round'}
        </button>
      </div>
    </div>
  );
}
