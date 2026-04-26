import { useReducer, useState, useLayoutEffect, useEffect, useRef } from 'react';
import { gameReducer, initialState } from './gameReducer';
import { getLegalDefenders, getWinner } from './gameLogic';
import { getEmbeddedGameId } from './embeddedGame';
import { loadGameInfo } from './serverGame';
import { tryRecordMove } from './serverMoves';
import { fetchNewMoves } from './serverPolling';
import type { RemoteMove } from './serverPolling';
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
  const mySeatRef = useRef<number | null>(null);

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
      mySeatRef.current = info.mySeat;
      const names = info.players.map(p => p.username) as [string, string, string, string];
      dispatch({ type: 'START_GAME', payload: { playerNames: names, dealSeed: info.dealSeed } });
    });
  }, []);

  // Track the latest state so the polling effect can read the up-to-date round info.
  const stateRef = useRef(state);
  useEffect(() => { stateRef.current = state; }, [state]);

  // In multiplayer, every player has their own browser, so the "pass the device"
  // transition screen makes no sense. Auto-confirm it.
  useEffect(() => {
    if (getEmbeddedGameId() == null) return;
    if (state.screen !== 'transition') return;
    dispatch({ type: 'TRANSITION_CONFIRMED' });
  }, [state.screen]);

  // Poll for moves played by other clients and apply them to local state.
  const lastMoveIdRef = useRef(0);
  useEffect(() => {
    if (getEmbeddedGameId() == null) return;
    if (state.round == null) return;

    const interval = setInterval(async () => {
      const moves = await fetchNewMoves(lastMoveIdRef.current);
      const next = moves[0];
      if (!next) return;
      lastMoveIdRef.current = next.move_id;
      applyRemoteMove(next, stateRef.current, dispatch);
    }, 1000);

    return () => clearInterval(interval);
  }, [state.round != null]);

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

      // Multiplayer: when it's not my turn, show a spectator view instead of the
      // action UI. mySeatRef is 1-based, currentIndex is 0-based.
      const mySeat = mySeatRef.current;
      if (mySeat != null && (mySeat - 1) !== currentIndex) {
        return (
          <div className="screen transition-screen">
            <div className="transition-inner">
              <p className="transition-instruction">Waiting for</p>
              <h2 className="transition-player-name">{currentPlayer.name}</h2>
              <div className="transition-seat">Seat {currentIndex + 1}</div>
              <p style={{ marginTop: 16, opacity: 0.6 }}>
                Score — Team A: {state.teamScores.A} · Team B: {state.teamScores.B}
              </p>
            </div>
          </div>
        );
      }

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

type Dispatch = (action: Parameters<typeof gameReducer>[1]) => void;

function applyRemoteMove(
  mv: RemoteMove,
  state: ReturnType<typeof gameReducer>,
  dispatch: Dispatch,
): void {
  if (!state.round) return;
  const seatIndex = (mv.seat_position - 1) as PlayerIndex;
  if (seatIndex !== state.round.currentPlayerIndex) {
    console.warn('serverPolling: seat mismatch — expected', state.round.currentPlayerIndex, 'got', seatIndex);
    return;
  }

  const hand = state.round.hands[seatIndex] ?? [];
  const kinds = mv.tile_kinds as TileKind[];

  if (kinds.length === 0) {
    dispatch({ type: 'PLAYER_PASSED' });
    return;
  }

  if (kinds.length === 2) {
    const k1 = kinds[0]!;
    const k2 = kinds[1]!;
    const t1 = hand.find(t => t.kind === k1);
    if (!t1) { console.warn('serverPolling: no tile of kind', k1); return; }
    const t2 = hand.find(t => t.id !== t1.id && t.kind === k2);
    if (!t2) { console.warn('serverPolling: no second tile of kind', k2); return; }

    if (state.round.currentAttack == null) {
      dispatch({ type: 'ATTACK_PLAYED', payload: { shogunTileId: t1.id, attackTileId: t2.id } });
    } else {
      dispatch({ type: 'DEFENSE_PLAYED', payload: { defenseTileId: t1.id, newAttackTileId: t2.id } });
    }
    return;
  }

  console.warn('serverPolling: unsupported tile_kinds count', kinds.length);
}

export default App;
