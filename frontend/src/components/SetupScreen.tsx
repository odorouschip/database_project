import { useState } from 'react';

interface Props {
  onStart: (names: [string, string, string, string]) => void;
}

const DEFAULT_NAMES = ['Player 1', 'Player 2', 'Player 3', 'Player 4'] as const;

export function SetupScreen({ onStart }: Props) {
  const [names, setNames] = useState<[string, string, string, string]>([...DEFAULT_NAMES]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = names.map(n => n.trim() || DEFAULT_NAMES[names.indexOf(n)]) as [string, string, string, string];
    onStart(trimmed);
  };

  const setName = (i: number, val: string) => {
    const updated = [...names] as [string, string, string, string];
    updated[i] = val;
    setNames(updated);
  };

  return (
    <div className="screen setup-screen">
      <div className="setup-inner">
        <h1 className="game-title">GOITA</h1>

        <form onSubmit={handleSubmit} className="setup-form">
          <div className="teams-grid">
            <div className="team-column">
              <div className="team-label team-a">Team A</div>
              {[0, 2].map(i => (
                <div key={i} className="player-input-group">
                  <label className="input-label">Seat {i + 1}</label>
                  <input
                    className="player-input"
                    type="text"
                    value={names[i]}
                    onChange={e => setName(i, e.target.value)}
                    maxLength={20}
                    placeholder={DEFAULT_NAMES[i]}
                  />
                </div>
              ))}
            </div>

            <div className="vs-divider">
              <span>vs</span>
            </div>

            <div className="team-column">
              <div className="team-label team-b">Team B</div>
              {[1, 3].map(i => (
                <div key={i} className="player-input-group">
                  <label className="input-label">Seat {i + 1}</label>
                  <input
                    className="player-input"
                    type="text"
                    value={names[i]}
                    onChange={e => setName(i, e.target.value)}
                    maxLength={20}
                    placeholder={DEFAULT_NAMES[i]}
                  />
                </div>
              ))}
            </div>
          </div>

          <button type="submit" className="btn-primary btn-large">
            Begin Game
          </button>
        </form>
      </div>
    </div>
  );
}
