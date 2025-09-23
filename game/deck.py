"""
Seedable PRNG and deck management for Ride the Bus.
"""
import random
from typing import List
from .types import Card, Rank, Suit


class SeededRNG:
    """Seedable random number generator for reproducible games."""
    
    def __init__(self, seed: int):
        self.seed = seed
        self._rng = random.Random(seed)
    
    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)
    
    def shuffle(self, lst: List) -> None:
        """Shuffle list in place using seeded RNG."""
        self._rng.shuffle(lst)
    
    def choice(self, lst: List):
        """Choose random element from list."""
        return self._rng.choice(lst)


def create_standard_deck() -> List[Card]:
    """Create a standard 52-card deck (no jokers, ace high)."""
    deck = []
    for suit in Suit:
        for rank in Rank:
            deck.append(Card(rank=rank, suit=suit))
    return deck


def shuffle_deck(deck: List[Card], rng: SeededRNG) -> None:
    """Shuffle deck in place using seeded RNG."""
    rng.shuffle(deck)


def deal_card(deck: List[Card]) -> Card:
    """Deal top card from deck. Raises IndexError if deck is empty."""
    if not deck:
        raise IndexError("Cannot deal from empty deck")
    return deck.pop(0)


def return_card_and_reshuffle(deck: List[Card], card: Card, rng: SeededRNG) -> None:
    """
    Return card to deck and reshuffle remaining deck.
    Used when a boundary card is drawn in R2/R3.
    """
    deck.insert(0, card)  # Return card to deck
    shuffle_deck(deck, rng)  # Reshuffle remaining deck