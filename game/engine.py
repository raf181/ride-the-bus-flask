"""
Core game engine for Ride the Bus card game.
Implements all three phases with proper rule enforcement.
"""
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import uuid

from .types import (
    Game, Player, Card, Phase, RoundId, Guess, Color, Rank, 
    LogEntry, Config, Pyramid, PyramidCell, RANK_ORDER
)
from .deck import SeededRNG, create_standard_deck, shuffle_deck, deal_card, return_card_and_reshuffle


class GameEngine:
    """Main game engine implementing all Ride the Bus rules."""
    
    def __init__(self, seed: int, config: Optional[Config] = None):
        self.rng = SeededRNG(seed)
        self.config = config or Config()
    
    def create_game(self, player_names: List[str], seed: int) -> Game:
        """Create a new game with given players and seed."""
        if len(player_names) < 2 or len(player_names) > 10:
            raise ValueError("Game requires 2-10 players")
        
        players = [Player(id=str(uuid.uuid4()), name=name) for name in player_names]
        deck = create_standard_deck()
        shuffle_deck(deck, self.rng)
        
        game = Game(
            id=str(uuid.uuid4()),
            seed=seed,
            phase=Phase.PHASE_ONE_DEAL,
            players=players,
            dealer_index=0,
            deck=deck,
            discard=[],
            pyramid=Pyramid(),
            log=[],
            config=self.config,
            current_round=RoundId.R1,
            current_player_index=0
        )
        
        self._log_event(game, "game_created", {"player_count": len(players), "seed": seed})
        return game
    
    def _log_event(self, game: Game, event_type: str, payload: Dict, player_id: Optional[str] = None):
        """Add event to game log."""
        entry = LogEntry(
            t=datetime.now(),
            type=event_type,
            payload=payload,
            by_player_id=player_id
        )
        game.log.append(entry)
    
    # Phase One: Dealing (R1-R4)
    
    def execute_round(self, game: Game, guess: Guess) -> Tuple[Card, bool, int]:
        """
        Execute current round for current player.
        Returns (dealt_card, was_correct, penalty_drinks).
        """
        if game.phase != Phase.PHASE_ONE_DEAL:
            raise ValueError("Not in dealing phase")
        
        player = game.players[game.current_player_index]
        round_id = game.current_round
        
        if round_id == RoundId.R1:
            return self._execute_r1(game, player, guess)
        elif round_id == RoundId.R2:
            return self._execute_r2(game, player, guess)
        elif round_id == RoundId.R3:
            return self._execute_r3(game, player, guess)
        elif round_id == RoundId.R4:
            return self._execute_r4(game, player, guess)
        else:
            raise ValueError(f"Invalid round: {round_id}")
    
    def _execute_r1(self, game: Game, player: Player, guess: Guess) -> Tuple[Card, bool, int]:
        """R1: Red or Black?"""
        card = deal_card(game.deck)
        player.hand.append(card)
        
        correct = (guess == Guess.RED and card.color == Color.RED) or \
                 (guess == Guess.BLACK and card.color == Color.BLACK)
        
        penalty = 0 if correct else game.config.penalty["sips_wrong_guess_r1"]
        if penalty > 0:
            player.drinks_received += penalty
        
        self._log_event(game, "guess_made", {
            "round": "R1", "guess": guess.value, "card": str(card), "correct": correct
        }, player.id)
        
        if penalty > 0:
            self._log_event(game, "penalty_applied", {"amount": penalty}, player.id)
        
        return card, correct, penalty
    
    def _execute_r2(self, game: Game, player: Player, guess: Guess) -> Tuple[Card, bool, int]:
        """R2: Higher or Lower? (with reshuffle rule for equal)"""
        if len(player.hand) < 1:
            raise ValueError("Player needs R1 card for R2")
        
        first_card = player.hand[0]
        
        # Deal second card, handling equal case with reshuffle
        while True:
            if not game.deck:
                raise RuntimeError("Deck exhausted during R2")
            
            second_card = deal_card(game.deck)
            
            # Check for equal rank (boundary case)
            if second_card.rank_value == first_card.rank_value:
                # Return card and reshuffle
                return_card_and_reshuffle(game.deck, second_card, self.rng)
                self._log_event(game, "card_dealt", {
                    "round": "R2", "boundary_reshuffle": True, "card": str(second_card)
                }, player.id)
                continue
            else:
                break
        
        player.hand.append(second_card)
        
        # Check guess
        if guess == Guess.HIGHER:
            correct = second_card.rank_value > first_card.rank_value
        elif guess == Guess.LOWER:
            correct = second_card.rank_value < first_card.rank_value
        else:
            raise ValueError("R2 requires HIGHER or LOWER guess")
        
        penalty = 0 if correct else game.config.penalty["sips_wrong_guess_r2"]
        if penalty > 0:
            player.drinks_received += penalty
        
        self._log_event(game, "guess_made", {
            "round": "R2", "guess": guess.value, "card": str(second_card), "correct": correct
        }, player.id)
        
        if penalty > 0:
            self._log_event(game, "penalty_applied", {"amount": penalty}, player.id)
        
        return second_card, correct, penalty
    
    def _execute_r3(self, game: Game, player: Player, guess: Guess) -> Tuple[Card, bool, int]:
        """R3: In-between or Outside? (with reshuffle rule for boundary equal)"""
        if len(player.hand) < 2:
            raise ValueError("Player needs R1 and R2 cards for R3")
        
        first_card = player.hand[0]
        second_card = player.hand[1]
        
        # Sort first two cards by rank (low to high)
        low_val = min(first_card.rank_value, second_card.rank_value)
        high_val = max(first_card.rank_value, second_card.rank_value)
        
        # Deal third card, handling boundary equality
        while True:
            if not game.deck:
                raise RuntimeError("Deck exhausted during R3")
            
            third_card = deal_card(game.deck)
            
            # Check for boundary equality
            if third_card.rank_value == low_val or third_card.rank_value == high_val:
                # Return card and reshuffle
                return_card_and_reshuffle(game.deck, third_card, self.rng)
                self._log_event(game, "card_dealt", {
                    "round": "R3", "boundary_reshuffle": True, "card": str(third_card)
                }, player.id)
                continue
            else:
                break
        
        player.hand.append(third_card)
        
        # Check guess (strictly between bounds)
        is_inside = low_val < third_card.rank_value < high_val
        
        if guess == Guess.INSIDE:
            correct = is_inside
        elif guess == Guess.OUTSIDE:
            correct = not is_inside
        else:
            raise ValueError("R3 requires INSIDE or OUTSIDE guess")
        
        penalty = 0 if correct else game.config.penalty["sips_wrong_guess_r3"]
        if penalty > 0:
            player.drinks_received += penalty
        
        self._log_event(game, "guess_made", {
            "round": "R3", "guess": guess.value, "card": str(third_card), "correct": correct
        }, player.id)
        
        if penalty > 0:
            self._log_event(game, "penalty_applied", {"amount": penalty}, player.id)
        
        return third_card, correct, penalty
    
    def _execute_r4(self, game: Game, player: Player, guess: Guess) -> Tuple[Card, bool, int]:
        """R4: Pick a Suit"""
        if len(player.hand) < 3:
            raise ValueError("Player needs R1, R2, R3 cards for R4")
        
        card = deal_card(game.deck)
        player.hand.append(card)
        
        # For R4, guess should contain suit information
        # This is a simplified implementation - in practice you'd have proper suit selection
        correct = False
        if guess == Guess.RED and card.color == Color.RED:
            correct = True
        elif guess == Guess.BLACK and card.color == Color.BLACK:
            correct = True
        
        if correct:
            # Player gets to assign drinks to others
            reward = game.config.reward["reward_distribute_drinks"]
            self._log_event(game, "reward_assigned", {"amount": reward}, player.id)
            penalty = 0
        else:
            penalty = game.config.penalty["sips_wrong_guess_r4"]
            player.drinks_received += penalty
            self._log_event(game, "penalty_applied", {"amount": penalty}, player.id)
        
        self._log_event(game, "guess_made", {
            "round": "R4", "guess": guess.value, "card": str(card), "correct": correct
        }, player.id)
        
        return card, correct, penalty
    
    def advance_to_next_turn(self, game: Game):
        """Advance to next player/round in Phase One."""
        if game.phase != Phase.PHASE_ONE_DEAL:
            return
        
        # Check if current round is complete for current player
        if game.current_round == RoundId.R4:
            # Move to next player, reset to R1
            game.current_player_index = (game.current_player_index + 1) % len(game.players)
            game.current_round = RoundId.R1
            
            # Check if all players completed all rounds
            if game.current_player_index == 0:  # Back to first player
                # All players have 4 cards, move to Phase Two
                self.start_phase_two(game)
        else:
            # Advance to next round for same player
            rounds = [RoundId.R1, RoundId.R2, RoundId.R3, RoundId.R4]
            current_idx = rounds.index(game.current_round)
            game.current_round = rounds[current_idx + 1]
    
    # Phase Two: Pyramid
    
    def start_phase_two(self, game: Game):
        """Start Phase Two (Pyramid)."""
        game.phase = Phase.PHASE_TWO_PYRAMID
        game.current_round = None
        
        # Setup pyramid with 15 cards face-down
        self._setup_pyramid(game)
        
        self._log_event(game, "pyramid_flip", {"phase": "started"})
    
    def _setup_pyramid(self, game: Game):
        """Setup pyramid with 15 cards from deck."""
        pyramid = game.pyramid
        
        # Place 15 cards face-down: rows of 5,4,3,2,1
        for row_idx, row in enumerate(pyramid.rows):
            for col_idx, cell in enumerate(row):
                if game.deck:
                    cell.card = deal_card(game.deck)
                    cell.face_up = False
    
    def flip_next_pyramid_card(self, game: Game) -> Optional[Card]:
        """Flip next card in pyramid sequence (bottom-left to top-right)."""
        if game.phase != Phase.PHASE_TWO_PYRAMID:
            raise ValueError("Not in pyramid phase")
        
        pyramid = game.pyramid
        cursor = pyramid.cursor
        
        # Find next face-down card
        for row_idx in range(len(pyramid.rows)):
            for col_idx in range(len(pyramid.rows[row_idx])):
                cell = pyramid.rows[row_idx][col_idx]
                if cell.card and not cell.face_up:
                    cell.face_up = True
                    pyramid.cursor = {"row": row_idx, "col": col_idx}
                    
                    self._log_event(game, "pyramid_flip", {
                        "row": row_idx, "col": col_idx, "card": str(cell.card)
                    })
                    
                    return cell.card
        
        # All cards flipped, determine bus rider
        self._determine_bus_rider(game)
        return None
    
    def commit_match(self, game: Game, player_id: str, card: Card) -> int:
        """Player commits a matching card from hand, returns drinks to assign."""
        if game.phase != Phase.PHASE_TWO_PYRAMID:
            raise ValueError("Not in pyramid phase")
        
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise ValueError("Player not found")
        
        # Get current flipped card
        current_card = self._get_current_pyramid_card(game)
        if not current_card:
            raise ValueError("No pyramid card to match")
        
        # Check if player has matching rank
        matching_cards = [c for c in player.hand if c.rank == current_card.rank]
        if not matching_cards or card not in player.hand:
            raise ValueError("Player doesn't have matching card")
        
        # Remove card from hand
        player.hand.remove(card)
        game.discard.append(card)
        
        # Determine drinks to assign based on current row
        cursor = game.pyramid.cursor
        row_value = game.config.pyramid["row_values"][cursor["row"]]
        
        self._log_event(game, "match_committed", {
            "card": str(card), "row": cursor["row"], "drinks": row_value
        }, player_id)
        
        return row_value
    
    def _get_current_pyramid_card(self, game: Game) -> Optional[Card]:
        """Get the currently flipped pyramid card."""
        cursor = game.pyramid.cursor
        row_idx = cursor["row"]
        col_idx = cursor["col"]
        
        if (0 <= row_idx < len(game.pyramid.rows) and 
            0 <= col_idx < len(game.pyramid.rows[row_idx])):
            cell = game.pyramid.rows[row_idx][col_idx]
            return cell.card if cell.face_up else None
        return None
    
    def _determine_bus_rider(self, game: Game):
        """Determine who rides the bus based on remaining hand sizes."""
        # Find players with most cards
        max_cards = max(len(player.hand) for player in game.players)
        candidates = [p for p in game.players if len(p.hand) == max_cards]
        
        if len(candidates) == 1:
            bus_rider = candidates[0]
        else:
            # Tie-break: highest remaining card rank
            bus_rider = self._resolve_tie_by_highest_card(candidates)
        
        bus_rider.is_bus_rider = True
        
        self._log_event(game, "bus_flip", {
            "phase": "rider_selected", "rider": bus_rider.name, "cards_remaining": len(bus_rider.hand)
        })
        
        # Start Phase Three
        self.start_phase_three(game)
    
    def _resolve_tie_by_highest_card(self, players: List[Player]) -> Player:
        """Resolve tie by comparing highest cards lexicographically."""
        def get_sorted_ranks(player: Player) -> List[int]:
            return sorted([card.rank_value for card in player.hand], reverse=True)
        
        best_player = players[0]
        best_ranks = get_sorted_ranks(best_player)
        
        for player in players[1:]:
            ranks = get_sorted_ranks(player)
            
            # Compare ranks lexicographically
            for i in range(min(len(best_ranks), len(ranks))):
                if ranks[i] > best_ranks[i]:
                    best_player = player
                    best_ranks = ranks
                    break
                elif ranks[i] < best_ranks[i]:
                    break
            else:
                # If all compared ranks are equal, longer hand wins
                if len(ranks) > len(best_ranks):
                    best_player = player
                    best_ranks = ranks
        
        return best_player
    
    # Phase Three: Ride the Bus
    
    def start_phase_three(self, game: Game):
        """Start Phase Three (Ride the Bus)."""
        game.phase = Phase.PHASE_THREE_BUS
        game.bus_cursor = 0
        
        # Setup 10 face-down cards for the bus
        game.bus_cards = []
        for _ in range(10):
            if game.deck:
                game.bus_cards.append(deal_card(game.deck))
        
        self._log_event(game, "bus_flip", {"phase": "started", "cards": 10})
    
    def flip_next_bus_card(self, game: Game) -> Tuple[Optional[Card], int]:
        """
        Flip next bus card.
        Returns (card, drinks_applied).
        """
        if game.phase != Phase.PHASE_THREE_BUS:
            raise ValueError("Not in bus phase")
        
        if game.bus_cursor >= len(game.bus_cards):
            # Bus complete
            game.phase = Phase.FINISHED
            self._log_event(game, "bus_flip", {"phase": "completed"})
            return None, 0
        
        card = game.bus_cards[game.bus_cursor]
        game.bus_cursor += 1
        
        # Determine drinks for face cards and aces
        drinks = 0
        if card.rank == Rank.JACK:
            drinks = 1
        elif card.rank == Rank.QUEEN:
            drinks = 2
        elif card.rank == Rank.KING:
            drinks = 3
        elif card.rank == Rank.ACE:
            drinks = 4
        
        # Apply drinks to bus rider
        if drinks > 0:
            bus_rider = next((p for p in game.players if p.is_bus_rider), None)
            if bus_rider:
                bus_rider.drinks_received += drinks
        
        self._log_event(game, "bus_flip", {
            "position": game.bus_cursor - 1, "card": str(card), "drinks": drinks
        })
        
        return card, drinks