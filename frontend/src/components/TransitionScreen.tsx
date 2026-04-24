import type { PlayerIndex } from '../types';

interface Props {
  playerName: string;
  playerIndex: PlayerIndex;
  onContinue: () => void;
}

export function TransitionScreen({ playerName, playerIndex, onContinue }: Props) {
  return (
    <div className="screen transition-screen">
      <div className="transition-inner">
        <p className="transition-instruction">Pass the device to</p>
        <h2 className="transition-player-name">{playerName}</h2>
        <div className="transition-seat">Seat {playerIndex + 1}</div>
        <button className="btn-primary btn-large" onClick={onContinue}>
          Continue
        </button>
      </div>
    </div>
  );
}
