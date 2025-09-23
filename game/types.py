"""
Core types and data structures for Ride the Bus card game.
"""
from enum import Enum
from typing import List, Dict, Optional, Literal, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


# Rank ordering for Ace high
RANK_ORDER = [
    Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN,
    Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
]


class Phase(Enum):
    PHASE_ONE_DEAL = "phase_one_deal"
    PHASE_TWO_PYRAMID = "phase_two_pyramid"
    PHASE_THREE_BUS = "phase_three_bus"
    FINISHED = "finished"


class RoundId(Enum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


class Color(Enum):
    RED = "red"
    BLACK = "black"


class Guess(Enum):
    # R1 guesses
    RED = "red"
    BLACK = "black"
    
    # R2 guesses
    HIGHER = "higher"
    LOWER = "lower"
    
    # R3 guesses
    INSIDE = "inside"
    OUTSIDE = "outside"


@dataclass
class Card:
    rank: Rank
    suit: Suit
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    def color(self) -> Color:
        return Color.RED if self.suit in [Suit.HEARTS, Suit.DIAMONDS] else Color.BLACK
    
    @property
    def rank_value(self) -> int:
        """Numeric value for rank comparison (Ace high)"""
        return RANK_ORDER.index(self.rank)
    
    def __str__(self):
        return f"{self.rank.value}{self.suit.value}"


@dataclass
class Player:
    id: str
    name: str
    hand: List[Card] = field(default_factory=list)
    drinks_assigned: int = 0
    drinks_received: int = 0
    is_bus_rider: bool = False


@dataclass
class PyramidCell:
    face_up: bool = False
    card: Optional[Card] = None


@dataclass
class Pyramid:
    rows: List[List[PyramidCell]] = field(default_factory=lambda: [
        [PyramidCell() for _ in range(5)],  # Bottom row: 5 cards
        [PyramidCell() for _ in range(4)],  # 4 cards
        [PyramidCell() for _ in range(3)],  # 3 cards
        [PyramidCell() for _ in range(2)],  # 2 cards
        [PyramidCell() for _ in range(1)],  # Top row: 1 card
    ])
    cursor: Dict[str, int] = field(default_factory=lambda: {"row": 0, "col": 0})


LogEntryType = Literal[
    "game_created", "player_joined", "card_dealt", "guess_made", 
    "penalty_applied", "reward_assigned", "pyramid_flip", "match_committed", 
    "bus_flip", "mode_toggle", "rematch_started"
]


@dataclass
class LogEntry:
    t: datetime
    type: LogEntryType
    payload: Dict
    by_player_id: Optional[str] = None


@dataclass
class Config:
    penalty: Dict[str, int] = field(default_factory=lambda: {
        "sips_wrong_guess_r1": 1,
        "sips_wrong_guess_r2": 1,
        "sips_wrong_guess_r3": 1,
        "sips_wrong_guess_r4": 1
    })
    reward: Dict[str, int] = field(default_factory=lambda: {
        "reward_distribute_drinks": 5
    })
    pyramid: Dict = field(default_factory=lambda: {
        "rows": [5, 4, 3, 2, 1],
        "row_values": [1, 2, 3, 4, 5],
        "top_card_alt": {"enable_shot_instead_of_5": True}
    })
    alcohol_mode: Dict = field(default_factory=lambda: {
        "enabled": True,
        "labels": {"drink_unit": "sip", "assign_action": "assign"},
        "non_alcohol_labels": {"drink_unit": "point", "assign_action": "give"}
    })
    house_rules: Dict[str, bool] = field(default_factory=lambda: {
        "allow_multiple_matches_per_player_per_flip": True,
        "limit_assign_target_once_per_flip": False
    })


@dataclass
class Game:
    id: str
    seed: int
    phase: Phase
    players: List[Player]
    dealer_index: int
    deck: List[Card]
    discard: List[Card]
    pyramid: Pyramid
    log: List[LogEntry]
    config: Config
    
    # Phase-specific state
    current_round: Optional[RoundId] = None
    current_player_index: int = 0
    bus_cards: List[Card] = field(default_factory=list)
    bus_cursor: int = 0