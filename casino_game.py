"""
Casino Ride the Bus - Core game types and logic
"""
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import uuid
from datetime import datetime


class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class Color(Enum):
    RED = "red"
    BLACK = "black"


class Round(Enum):
    ROUND1 = 1  # Red or Black
    ROUND2 = 2  # Higher/Lower
    ROUND3 = 3  # Inside/Outside
    ROUND4 = 4  # Suit guess


class GameStatus(Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CASHED_OUT = "cashed_out"


@dataclass
class Card:
    rank: Rank
    suit: Suit
    
    @property
    def color(self) -> Color:
        return Color.RED if self.suit in [Suit.HEARTS, Suit.DIAMONDS] else Color.BLACK
    
    @property
    def value(self) -> int:
        return self.rank.value
    
    def __str__(self):
        return f"{self.rank.name}{self.suit.value}"


@dataclass
class GameState:
    game_id: str
    current_round: Round
    cards_drawn: List[Card]
    bet_amount: float
    current_winnings: float
    status: GameStatus
    deck: List[Card]
    game_history: List[Dict]
    
    @property
    def potential_winnings(self) -> float:
        """Calculate potential winnings if current round is won"""
        multiplier = self.get_round_multiplier(self.current_round)
        if self.current_round == Round.ROUND1:
            return self.bet_amount * multiplier
        else:
            return self.current_winnings * multiplier
    
    def get_round_multiplier(self, round_num: Round) -> float:
        """Get the payout multiplier for each round"""
        multipliers = {
            Round.ROUND1: 2.0,  # Double your bet
            Round.ROUND2: 2.0,  # Double current winnings
            Round.ROUND3: 3.0,  # Triple current winnings
            Round.ROUND4: 4.0,  # Quadruple current winnings
        }
        return multipliers.get(round_num, 1.0)


@dataclass
class StrategyRecommendation:
    action: str  # "pick_red", "pick_black", "pick_higher", "pick_lower", "pick_inside", "pick_outside", "cash_out", "forfeit"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    expected_value: float
    probability: float


class CasinoRideTheBus:
    """Main game engine for Casino Ride the Bus"""
    
    def __init__(self, seed: Optional[int] = None):
        import random
        if seed:
            random.seed(seed)
        self.rng = random
    
    def create_deck(self) -> List[Card]:
        """Create a standard 52-card deck"""
        deck = []
        for suit in Suit:
            for rank in Rank:
                deck.append(Card(rank, suit))
        self.rng.shuffle(deck)
        return deck
    
    def start_new_game(self, bet_amount: float) -> GameState:
        """Start a new game with the given bet amount"""
        return GameState(
            game_id=str(uuid.uuid4()),
            current_round=Round.ROUND1,
            cards_drawn=[],
            bet_amount=bet_amount,
            current_winnings=0.0,
            status=GameStatus.ACTIVE,
            deck=self.create_deck(),
            game_history=[]
        )
    
    def draw_card(self, game: GameState) -> Card:
        """Draw the next card from the deck"""
        if not game.deck:
            raise ValueError("Deck is empty")
        card = game.deck.pop(0)
        game.cards_drawn.append(card)
        return card
    
    def make_guess(self, game: GameState, guess: str) -> Tuple[bool, Card, float]:
        """
        Make a guess for the current round
        Returns: (is_correct, card_drawn, winnings)
        """
        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game is not active")
        
        card = self.draw_card(game)
        is_correct = self._check_guess(game, guess, card)
        
        if is_correct:
            # Win the round
            if game.current_round == Round.ROUND1:
                game.current_winnings = game.bet_amount * game.get_round_multiplier(game.current_round)
            else:
                game.current_winnings *= game.get_round_multiplier(game.current_round)
            
            # Move to next round or win the game
            if game.current_round == Round.ROUND4:
                game.status = GameStatus.WON
            else:
                game.current_round = Round(game.current_round.value + 1)
        else:
            # Lose the game
            game.status = GameStatus.LOST
            game.current_winnings = 0.0
        
        # Record the move
        game.game_history.append({
            "round": game.current_round.value,
            "guess": guess,
            "card": str(card),
            "correct": is_correct,
            "winnings": game.current_winnings,
            "timestamp": datetime.now().isoformat()
        })
        
        return is_correct, card, game.current_winnings
    
    def cash_out(self, game: GameState) -> float:
        """Cash out current winnings"""
        if game.status != GameStatus.ACTIVE or game.current_round == Round.ROUND1:
            raise ValueError("Cannot cash out at this time")
        
        winnings = game.current_winnings
        game.status = GameStatus.CASHED_OUT
        return winnings
    
    def _check_guess(self, game: GameState, guess: str, card: Card) -> bool:
        """Check if the guess is correct for the current round"""
        if game.current_round == Round.ROUND1:
            return self._check_round1(guess, card)
        elif game.current_round == Round.ROUND2:
            return self._check_round2(guess, card, game.cards_drawn[0])
        elif game.current_round == Round.ROUND3:
            return self._check_round3(guess, card, game.cards_drawn[0], game.cards_drawn[1])
        elif game.current_round == Round.ROUND4:
            return self._check_round4(guess, card, game.cards_drawn)
        return False
    
    def _check_round1(self, guess: str, card: Card) -> bool:
        """Round 1: Red or Black"""
        return (guess.lower() == "red" and card.color == Color.RED) or \
               (guess.lower() == "black" and card.color == Color.BLACK)
    
    def _check_round2(self, guess: str, card: Card, first_card: Card) -> bool:
        """Round 2: Higher/Equal or Lower"""
        if guess.lower() == "higher":
            return card.value >= first_card.value
        elif guess.lower() == "lower":
            return card.value <= first_card.value
        return False
    
    def _check_round3(self, guess: str, card: Card, first_card: Card, second_card: Card) -> bool:
        """Round 3: Inside or Outside the range"""
        low = min(first_card.value, second_card.value)
        high = max(first_card.value, second_card.value)
        
        if guess.lower() == "inside":
            return low < card.value < high
        elif guess.lower() == "outside":
            return card.value <= low or card.value >= high
        return False
    
    def _check_round4(self, guess: str, card: Card, previous_cards: List[Card]) -> bool:
        """Round 4: Guess the suit (must not be on the board)"""
        # Get suits already on the board
        used_suits = {c.suit.name.lower() for c in previous_cards[:3]}
        
        # Check if guessed suit matches the card and isn't already used
        guessed_suit = guess.lower()
        card_suit = card.suit.name.lower()
        
        return guessed_suit == card_suit and card_suit not in used_suits
    
    def get_strategy_recommendation(self, game: GameState) -> StrategyRecommendation:
        """Get optimal strategy recommendation based on current game state"""
        if game.current_round == Round.ROUND1:
            return self._strategy_round1()
        elif game.current_round == Round.ROUND2:
            return self._strategy_round2(game.cards_drawn[0])
        elif game.current_round == Round.ROUND3:
            return self._strategy_round3(game.cards_drawn[0], game.cards_drawn[1])
        elif game.current_round == Round.ROUND4:
            return self._strategy_round4(game.cards_drawn[:3])
        
        return StrategyRecommendation("cash_out", 0.0, "Unknown round", 0.0, 0.0)
    
    def _strategy_round1(self) -> StrategyRecommendation:
        """Round 1 strategy: Pick either color consistently"""
        return StrategyRecommendation(
            action="pick_red",
            confidence=0.5,
            reasoning="50/50 chance. Pick red consistently for pattern.",
            expected_value=1.0,  # Even odds
            probability=0.5
        )
    
    def _strategy_round2(self, first_card: Card) -> StrategyRecommendation:
        """Round 2 strategy based on first card value"""
        value = first_card.value
        
        if 2 <= value <= 5:
            # Low cards: pick higher
            prob = (14 - value) / 12  # Cards higher than first card / remaining cards
            return StrategyRecommendation(
                action="pick_higher",
                confidence=0.8,
                reasoning=f"Card {value} is low. {prob:.1%} chance of higher card.",
                expected_value=prob * 2.0,
                probability=prob
            )
        elif 6 <= value <= 10:
            # Middle cards: forfeit (too risky)
            return StrategyRecommendation(
                action="cash_out",
                confidence=0.9,
                reasoning=f"Card {value} is in danger zone. Cash out to preserve winnings.",
                expected_value=1.0,  # Keep current winnings
                probability=1.0
            )
        else:
            # High cards (J, Q, K, A): pick lower
            prob = (value - 2) / 12  # Cards lower than first card / remaining cards
            return StrategyRecommendation(
                action="pick_lower",
                confidence=0.8,
                reasoning=f"Card {value} is high. {prob:.1%} chance of lower card.",
                expected_value=prob * 2.0,
                probability=prob
            )
    
    def _strategy_round3(self, first_card: Card, second_card: Card) -> StrategyRecommendation:
        """Round 3 strategy based on card gap"""
        low = min(first_card.value, second_card.value)
        high = max(first_card.value, second_card.value)
        gap = high - low
        
        if gap == 0:  # Pair
            return StrategyRecommendation(
                action="pick_outside",
                confidence=0.95,
                reasoning="Pair of cards. Very high chance of outside.",
                expected_value=2.7,
                probability=0.9
            )
        elif gap == 1:  # Connecting cards
            return StrategyRecommendation(
                action="pick_outside",
                confidence=0.95,
                reasoning="Connecting cards (no gap). Very high chance of outside.",
                expected_value=2.7,
                probability=0.9
            )
        elif gap == 2:  # 1-card gap
            return StrategyRecommendation(
                action="pick_outside",
                confidence=0.85,
                reasoning="1-card gap. High chance of outside.",
                expected_value=2.4,
                probability=0.8
            )
        elif gap >= 9:  # 9+ card gap
            inside_prob = (gap - 1) / 12
            return StrategyRecommendation(
                action="pick_inside",
                confidence=0.8,
                reasoning=f"{gap}-card gap. {inside_prob:.1%} chance of inside.",
                expected_value=inside_prob * 3.0,
                probability=inside_prob
            )
        else:  # 2-8 card gap
            return StrategyRecommendation(
                action="cash_out",
                confidence=0.9,
                reasoning=f"{gap}-card gap is in danger zone. Cash out recommended.",
                expected_value=2.0,  # Keep current winnings
                probability=1.0
            )
    
    def _strategy_round4(self, previous_cards: List[Card]) -> StrategyRecommendation:
        """Round 4 strategy: pick suit not on board"""
        used_suits = {card.suit for card in previous_cards}
        available_suits = [suit for suit in Suit if suit not in used_suits]
        
        if available_suits:
            prob = 1.0 / len(available_suits)
            suit_name = available_suits[0].name.lower()
            return StrategyRecommendation(
                action=f"pick_{suit_name}",
                confidence=0.7,
                reasoning=f"Pick {suit_name} (not on board). {prob:.1%} chance.",
                expected_value=prob * 4.0,
                probability=prob
            )
        else:
            return StrategyRecommendation(
                action="cash_out",
                confidence=1.0,
                reasoning="All suits are on board. Impossible to win.",
                expected_value=3.0,
                probability=0.0
            )