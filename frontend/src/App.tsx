import { useReducer, useState, useLayoutEffect, useEffect, useRef } from 'react';
import { gameReducer, initialState } from './gameReducer';
import { getLegalDefenders, getWinner } from './gameLogic';
import { getEmbeddedGameId } from './embeddedGame';
import { loadGameInfo } from './serverGame';
import { tryRecordMove } from './serverMoves';
import { SetupScreen } from './components/SetupScreen';
import { TransitionScreen } from './components/TransitionScreen';
import { PlayerTurnScreen } from './components/PlayerTurnScreen';
import { SpecialPawnScreen } from './components/SpecialPawnScreen';
import { RoundOverScreen } from './components/RoundOverScreen';
import { GameOverScreen } from './components/GameOverScreen';
import type { PlayerIndex, TileKind } from './types';

const AUTOSTART_KEY = 'goita_autostart';

export function App() {
  const [state, dispatch] = useReducer(gameReducer, initialState);
  const [matchSaved, setMatchSaved] = useState(true);
  const [savingResult, setSavingResult] = useState(false);
  const autostartOnce = useRef(false);

  // Rematch: continue with same four names (parent navigates to /play/<newId>)
  useEffect(() => {
    if (autostartOnce.current) return;
    const raw = sessionStorage.getItem(AUTOSTART_KEY);
    if (!raw) return;
    autostartOnce.current = true;
    try {
      const names = JSON.parse(raw) as [string, string, string, string];
      sessionStorage.removeItem(AUTOSTART_KEY);
      dispatch({ type: 'START_GAME', payload: { playerNames: names } });
    } catch {
      autostartOnce.current = false;
    }
  }, []);

  // Embedded game: auto-load real player names from server and skip SetupScreen
  useEffect(() => {
    if (autostartOnce.current) return;
    if (getEmbeddedGameId() == null) return;
    autostartOnce.current = true;
    void loadGameInfo().then(info => {
      if (!info) {
        autostartOnce.current = false;
        return;
      }
      const names = info.players.map(p => p.username) as [string, string, string, string];
      dispatch({ type: 'START_GAME', payload: { playerNames: names } });
    });
  }, []);

  // When hosted on the play page, record the result as soon as game over is shown
  useLayoutEffect(() => {
    if (state.screen !== 'game_over') return;

    const gid = getEmbeddedGameId();
    if (gid == null) {
      setMatchSaved(true);
      setSavingResult(false);
      return;
    }

    setMatchSaved(false);
    setSavingResult(true);
    const winner = getWinner(state.teamScores) ?? 'A';
    const body = {
      team1_score: state.teamScores.A,
      team2_score: state.teamScores.B,
      winning_team_number: winner === 'A' ? 1 : 2,
    };

    let cancelled = false;
    fetch(`/api/match/${gid}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    })
      .then(async res => {
        if (cancelled) return;
        const data = (await res.json().catch(() => ({}))) as { message?: string };
        if (!res.ok) {
          alert(data.message || 'Could not save match — try refreshing.');
          return;
        }
        setMatchSaved(true);
      })
      .catch(() => {
        if (cancelled) return;
        alert('Could not save match — check your connection.');
      })
      .finally(() => {
        if (!cancelled) setSavingResult(false);
      });

    return () => {
      cancelled = true;
    };
  }, [state.screen, state.teamScores.A, state.teamScores.B]);

  const embedded = getEmbeddedGameId() != null;

  switch (state.screen) {
    case 'setup':
      return (
        <SetupScreen
          onStart={names => dispatch({ type: 'START_GAME', payload: { playerNames: names } })}
        />
      );

    case 'transition': {
      const { nextPlayerIndex } = state.transition!;
      const playerName = state.players?.[nextPlayerIndex]?.name ?? `Player ${nextPlayerIndex + 1}`;
      return (
        <TransitionScreen
          playerName={playerName}
          playerIndex={nextPlayerIndex}
          onContinue={() => dispatch({ type: 'TRANSITION_CONFIRMED' })}
        />
      );
    }

    case 'player_turn': {
      const round = state.round!;
      const currentIndex = round.currentPlayerIndex;
      const currentPlayer = state.players![currentIndex]!;
      const hand = round.hands[currentIndex] ?? [];
      const legalDefenders = round.currentAttack
        ? getLegalDefenders(hand, round.currentAttack.attackTile)
        : [];

      return (
        <PlayerTurnScreen
          currentPlayer={currentPlayer}
          hand={hand}
          currentAttack={round.currentAttack}
          teamScores={state.teamScores}
          players={state.players!}
          hands={round.hands}
          boardHistory={round.boardHistory}
          roundNumber={round.roundNumber}
          legalDefenders={legalDefenders}
          onAttack={(s, a) => {
            const sh = round.hands[currentIndex]?.find(t => t.id === s);
            const at = round.hands[currentIndex]?.find(t => t.id === a);
            if (sh && at) {
              tryRecordMove({
                roundNumber: round.roundNumber,
                playerIndex: currentIndex,
                tileKinds: [sh.kind, at.kind],
              });
            }
            dispatch({ type: 'ATTACK_PLAYED', payload: { shogunTileId: s, attackTileId: a } });
          }}
          onDefend={(d, a) => {
            const de = round.hands[currentIndex]?.find(t => t.id === d);
            const na = round.hands[currentIndex]?.find(t => t.id === a);
            if (de && na) {
              tryRecordMove({
                roundNumber: round.roundNumber,
                playerIndex: currentIndex,
                tileKinds: [de.kind, na.kind],
              });
            }
            dispatch({ type: 'DEFENSE_PLAYED', payload: { defenseTileId: d, newAttackTileId: a } });
          }}
          onPass={() => {
            tryRecordMove({ roundNumber: round.roundNumber, playerIndex: currentIndex, tileKinds: [] });
            dispatch({ type: 'PLAYER_PASSED' });
          }}
        />
      );
    }

    case 'special_pawn': {
      const round = state.round!;
      const trigger = round.specialPawnTrigger!;
      const currentViewerIndex: PlayerIndex = round.pawn5PendingPartner
        ? round.pawn5PendingPartner.partnerIndex
        : round.currentPlayerIndex;

      return (
        <SpecialPawnScreen
          trigger={trigger}
          players={state.players!}
          pawn5PendingPartner={round.pawn5PendingPartner}
          currentViewerIndex={currentViewerIndex}
          onAutoWin={() => {
            let tileKinds: TileKind[] = [];
            if (trigger.type === 'pawn7' && 'nonPawnTile' in trigger) {
              tileKinds = [trigger.nonPawnTile.kind];
            } else if (trigger.type === 'pawn6' && 'nonPawnTiles' in trigger) {
              tileKinds = [trigger.nonPawnTiles[0]!.kind, trigger.nonPawnTiles[1]!.kind];
            }
            const pi: PlayerIndex =
              'playerIndex' in trigger ? (trigger as { playerIndex: PlayerIndex }).playerIndex : currentViewerIndex;
            tryRecordMove({ roundNumber: round.roundNumber, playerIndex: pi, tileKinds });
            dispatch({ type: 'SPECIAL_PAWN_AUTO_WIN' });
          }}
          onPawn5Reveal={() => {
            if (trigger.type === 'pawn5') {
              tryRecordMove({
                roundNumber: round.roundNumber,
                playerIndex: trigger.playerIndex,
                tileKinds: [],
              });
            }
            dispatch({ type: 'PAWN5_REVEAL' });
          }}
          onPawn5PartnerChoice={choice => {
            if (round.pawn5PendingPartner) {
              tryRecordMove({
                roundNumber: round.roundNumber,
                playerIndex: round.pawn5PendingPartner.partnerIndex,
                tileKinds: [],
              });
            }
            dispatch({ type: 'PAWN5_PARTNER_CHOICE', payload: { choice } });
          }}
        />
      );
    }

    case 'round_over': {
      const round = state.round!;
      return (
        <RoundOverScreen
          roundResult={round.roundResult!}
          teamScores={state.teamScores}
          players={state.players!}
          roundNumber={round.roundNumber}
          onNextRound={() => dispatch({ type: 'NEXT_ROUND' })}
        />
      );
    }

    case 'game_over': {
      const winner = getWinner(state.teamScores) ?? 'A';
      return (
        <GameOverScreen
          winningTeam={winner}
          players={state.players!}
          finalScores={state.teamScores}
          savingResult={embedded && savingResult}
          matchSaved={!embedded || matchSaved}
          onBackToLobby={embedded ? () => { (window.top ?? window).location.href = '/matchmaking'; } : undefined}
          onRestart={async () => {
            if (embedded && (!matchSaved || savingResult)) return;
            const gid = getEmbeddedGameId();
            if (gid == null) {
              dispatch({ type: 'RESTART_GAME' });
              return;
            }
            try {
              const res = await fetch(`/api/match/${gid}/rematch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
              });
              const data = (await res.json().catch(() => ({}))) as { message?: string; game_id?: number };
              if (!res.ok) {
                alert(data.message || 'Could not start a new game with the same group.');
                return;
              }
              if (typeof data.game_id !== 'number') {
                alert('Invalid server response.');
                return;
              }
              const names = state.players!.map(p => p.name) as [string, string, string, string];
              sessionStorage.setItem(AUTOSTART_KEY, JSON.stringify(names));
              (window.top ?? window).location.href = `/play/${data.game_id}`;
            } catch {
              alert('Network error');
            }
          }}
        />
      );
    }

    default:
      return null;
  }
}

export default App;
