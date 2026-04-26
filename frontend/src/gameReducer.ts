import type { GameState, RoundState, PlayerIndex } from './types';
import {
  initRound, nextPlayer, getTeamId,
  computeRoundEndResult, isGameOver,
  checkPawn5Partner, computeSpecialPawnScore,
  removeTileFromHand,
} from './gameLogic';

export type GameAction =
  | { type: 'START_GAME'; payload: { playerNames: [string, string, string, string]; dealSeed?: number | null } }
  | { type: 'TRANSITION_CONFIRMED' }
  | { type: 'ATTACK_PLAYED'; payload: { shogunTileId: number; attackTileId: number } }
  | { type: 'DEFENSE_PLAYED'; payload: { defenseTileId: number; newAttackTileId: number } }
  | { type: 'PLAYER_PASSED' }
  | { type: 'SPECIAL_PAWN_AUTO_WIN' }
  | { type: 'PAWN5_REVEAL' }
  | { type: 'PAWN5_PARTNER_CHOICE'; payload: { choice: 'play_normal' | 'redeal' } }
  | { type: 'NEXT_ROUND' }
  | { type: 'RESTART_GAME' };

export const initialState: GameState = {
  screen: 'setup',
  players: null,
  teamScores: { A: 0, B: 0 },
  round: null,
  transition: null,
  dealSeed: null,
};

function afterDeal(state: GameState, round: RoundState): GameState {
  const afterScreen = round.specialPawnTrigger ? 'special_pawn' : 'player_turn';
  return {
    ...state,
    round,
    screen: 'transition',
    transition: { nextPlayerIndex: round.dealerIndex, afterScreen },
  };
}

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {

    case 'START_GAME': {
      const players = action.payload.playerNames.map((name, i) => ({
        index: i as PlayerIndex,
        name,
        teamId: getTeamId(i as PlayerIndex),
      })) as GameState['players'];
      const dealSeed = action.payload.dealSeed ?? null;
      const round = initRound(1, 0, dealSeed);
      return afterDeal({ ...state, players, teamScores: { A: 0, B: 0 }, dealSeed }, round);
    }

    case 'TRANSITION_CONFIRMED': {
      const { afterScreen } = state.transition!;
      return { ...state, screen: afterScreen, transition: null };
    }

    case 'ATTACK_PLAYED': {
      const round = state.round!;
      const { shogunTileId, attackTileId } = action.payload;
      const currentIndex = round.currentPlayerIndex;

      const shogunTile = round.hands[currentIndex]!.find(t => t.id === shogunTileId)!;
      const attackTile = round.hands[currentIndex]!.find(t => t.id === attackTileId)!;

      let newHand = removeTileFromHand(round.hands[currentIndex]!, shogunTileId);
      newHand = removeTileFromHand(newHand, attackTileId);
      const newHands = { ...round.hands, [currentIndex]: newHand };
      const newAttack = { attackerIndex: currentIndex, shogunTile, attackTile, consecutivePasses: 0 };

      const newBoardHistory = {
        ...round.boardHistory,
        [currentIndex]: {
          ...round.boardHistory[currentIndex],
          attackTiles: [...round.boardHistory[currentIndex]!.attackTiles, attackTile],
        },
      };

      if (newHand.length === 0) {
        const roundResult = computeRoundEndResult(currentIndex, newAttack);
        const newScores = { ...state.teamScores, [roundResult.winningTeam]: state.teamScores[roundResult.winningTeam] + roundResult.pointsScored };
        return { ...state, teamScores: newScores, screen: 'round_over', round: { ...round, hands: newHands, currentAttack: newAttack, roundResult, boardHistory: newBoardHistory }, transition: null };
      }

      const nextIndex = nextPlayer(currentIndex);
      return {
        ...state,
        screen: 'transition',
        round: { ...round, hands: newHands, currentAttack: newAttack, currentPlayerIndex: nextIndex, boardHistory: newBoardHistory },
        transition: { nextPlayerIndex: nextIndex, afterScreen: 'player_turn' },
      };
    }

    case 'DEFENSE_PLAYED': {
      const round = state.round!;
      const { defenseTileId, newAttackTileId } = action.payload;
      const currentIndex = round.currentPlayerIndex;

      const defenseTile = round.hands[currentIndex]!.find(t => t.id === defenseTileId)!;
      const newAttackTile = round.hands[currentIndex]!.find(t => t.id === newAttackTileId)!;

      let newHand = removeTileFromHand(round.hands[currentIndex]!, defenseTileId);
      newHand = removeTileFromHand(newHand, newAttackTileId);
      const newHands = { ...round.hands, [currentIndex]: newHand };
      const newAttack = { attackerIndex: currentIndex, shogunTile: defenseTile, attackTile: newAttackTile, consecutivePasses: 0 };

      // Record defense tile (受け) and new attack tile (攻め) on the public board
      const newBoardHistory = {
        ...round.boardHistory,
        [currentIndex]: {
          attackTiles: [...round.boardHistory[currentIndex]!.attackTiles, newAttackTile],
          defenseTiles: [...round.boardHistory[currentIndex]!.defenseTiles, defenseTile],
        },
      };

      if (newHand.length === 0) {
        const roundResult = computeRoundEndResult(currentIndex, newAttack);
        const newScores = { ...state.teamScores, [roundResult.winningTeam]: state.teamScores[roundResult.winningTeam] + roundResult.pointsScored };
        return { ...state, teamScores: newScores, screen: 'round_over', round: { ...round, hands: newHands, currentAttack: newAttack, roundResult, boardHistory: newBoardHistory }, transition: null };
      }

      const nextIndex = nextPlayer(currentIndex);
      return {
        ...state,
        screen: 'transition',
        round: { ...round, hands: newHands, currentAttack: newAttack, currentPlayerIndex: nextIndex, boardHistory: newBoardHistory },
        transition: { nextPlayerIndex: nextIndex, afterScreen: 'player_turn' },
      };
    }

    case 'PLAYER_PASSED': {
      const round = state.round!;
      const currentAttack = round.currentAttack!;
      const newPassCount = currentAttack.consecutivePasses + 1;

      if (newPassCount >= 3) {
        const attackerIndex = currentAttack.attackerIndex;
        // Clear the attack entirely -> the returning attacker plays a fresh attack (not a defense)
        return {
          ...state,
          screen: 'transition',
          round: { ...round, currentPlayerIndex: attackerIndex, currentAttack: null },
          transition: { nextPlayerIndex: attackerIndex, afterScreen: 'player_turn' },
        };
      }

      const nextIndex = nextPlayer(round.currentPlayerIndex);
      return {
        ...state,
        screen: 'transition',
        round: { ...round, currentPlayerIndex: nextIndex, currentAttack: { ...currentAttack, consecutivePasses: newPassCount } },
        transition: { nextPlayerIndex: nextIndex, afterScreen: 'player_turn' },
      };
    }

    case 'SPECIAL_PAWN_AUTO_WIN': {
      const round = state.round!;
      const trigger = round.specialPawnTrigger!;
      const score = computeSpecialPawnScore(trigger);
      const winnerIndex = (trigger as { playerIndex: PlayerIndex }).playerIndex;
      const winningTeam = getTeamId(winnerIndex);
      const newScores = { ...state.teamScores, [winningTeam]: state.teamScores[winningTeam] + score };
      const roundResult = { winningTeam, pointsScored: score, reason: trigger.type as 'pawn8' | 'pawn7' | 'pawn6' };
      return { ...state, teamScores: newScores, screen: 'round_over', round: { ...round, roundResult, specialPawnTrigger: null }, transition: null };
    }

    case 'PAWN5_REVEAL': {
      const round = state.round!;
      const trigger = round.specialPawnTrigger!;
      if (trigger.type !== 'pawn5') return state;

      const partnerHas5 = checkPawn5Partner(round.hands, trigger.playerIndex);

      if (partnerHas5) {
        const winningTeam = getTeamId(trigger.playerIndex);
        const newScores = { ...state.teamScores, [winningTeam]: 150 };
        const roundResult = { winningTeam, pointsScored: 150 - state.teamScores[winningTeam], reason: 'pawn5_both_partners' as const };
        return { ...state, teamScores: newScores, screen: 'round_over', round: { ...round, roundResult, specialPawnTrigger: null }, transition: null };
      }

      // Partner must decide if they wish to play, transition to partner
      const partnerIndex = ((trigger.playerIndex + 2) % 4) as PlayerIndex;
      const newRound: RoundState = { ...round, pawn5PendingPartner: { triggeringPlayer: trigger.playerIndex, partnerIndex: partnerIndex } };
      return {
        ...state,
        screen: 'transition',
        round: newRound,
        transition: { nextPlayerIndex: partnerIndex, afterScreen: 'special_pawn' },
      };
    }

    case 'PAWN5_PARTNER_CHOICE': {
      const round = state.round!;
      const { choice } = action.payload;

      if (choice === 'play_normal') {
        const newRound: RoundState = {
          ...round,
          specialPawnTrigger: null,
          pawn5PendingPartner: null,
          currentAttack: null,
          currentPlayerIndex: round.dealerIndex,
        };
        return {
          ...state,
          screen: 'transition',
          round: newRound,
          transition: { nextPlayerIndex: round.dealerIndex, afterScreen: 'player_turn' },
        };
      }

      // Redeal -> same dealer, same round number
      const newRound = initRound(round.roundNumber, round.dealerIndex, state.dealSeed);
      return afterDeal(state, newRound);
    }

    case 'NEXT_ROUND': {
      if (isGameOver(state.teamScores)) {
        return { ...state, screen: 'game_over', round: null, transition: null };
      }
      const newDealerIndex = nextPlayer(state.round!.dealerIndex);
      const newRoundNumber = (state.round?.roundNumber ?? 0) + 1;
      const newRound = initRound(newRoundNumber, newDealerIndex, state.dealSeed);
      return afterDeal(state, newRound);
    }

    case 'RESTART_GAME': {
      if (!state.players || state.players.length !== 4) {
        return { ...initialState };
      }
      const playerNames = state.players.map(p => p.name) as [string, string, string, string];
      const players = playerNames.map((name, i) => ({
        index: i as PlayerIndex,
        name,
        teamId: getTeamId(i as PlayerIndex),
      })) as GameState['players'];
      const round = initRound(1, 0, state.dealSeed);
      return afterDeal({ ...state, players, teamScores: { A: 0, B: 0 } }, round);
    }

    default:
      return state;
  }
}
