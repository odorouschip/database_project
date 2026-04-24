import { useReducer } from 'react';
import { gameReducer, initialState } from './gameReducer';
import { getLegalDefenders, getWinner } from './gameLogic';
import { SetupScreen } from './components/SetupScreen';
import { TransitionScreen } from './components/TransitionScreen';
import { PlayerTurnScreen } from './components/PlayerTurnScreen';
import { SpecialPawnScreen } from './components/SpecialPawnScreen';
import { RoundOverScreen } from './components/RoundOverScreen';
import { GameOverScreen } from './components/GameOverScreen';
import type { PlayerIndex } from './types';

export function App() {
  const [state, dispatch] = useReducer(gameReducer, initialState);

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
          onAttack={(s, a) => dispatch({ type: 'ATTACK_PLAYED', payload: { shogunTileId: s, attackTileId: a } })}
          onDefend={(d, a) => dispatch({ type: 'DEFENSE_PLAYED', payload: { defenseTileId: d, newAttackTileId: a } })}
          onPass={() => dispatch({ type: 'PLAYER_PASSED' })}
        />
      );
    }

    case 'special_pawn': {
      const round = state.round!;
      const trigger = round.specialPawnTrigger!;
      // After PAWN5_REVEAL, we go to transition -> the viewer is whoever is in transition.nextPlayerIndex
      // On special_pawn screen directly, the viewer is the dealer
      const currentViewerIndex: PlayerIndex = round.pawn5PendingPartner
        ? round.pawn5PendingPartner.partnerIndex
        : round.currentPlayerIndex;

      return (
        <SpecialPawnScreen
          trigger={trigger}
          players={state.players!}
          pawn5PendingPartner={round.pawn5PendingPartner}
          currentViewerIndex={currentViewerIndex}
          onAutoWin={() => dispatch({ type: 'SPECIAL_PAWN_AUTO_WIN' })}
          onPawn5Reveal={() => dispatch({ type: 'PAWN5_REVEAL' })}
          onPawn5PartnerChoice={choice => dispatch({ type: 'PAWN5_PARTNER_CHOICE', payload: { choice } })}
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
          onRestart={() => dispatch({ type: 'RESTART_GAME' })}
        />
      );
    }

    default:
      return null;
  }
}

export default App;
