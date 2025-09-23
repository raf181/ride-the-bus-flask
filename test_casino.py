"""
Test the casino Ride the Bus game engine
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from casino_game import CasinoRideTheBus, Round, GameStatus

def test_full_game():
    """Test a complete game scenario"""
    print("🎰 Testing Casino Ride the Bus 🎰\n")
    
    # Create game engine
    engine = CasinoRideTheBus(seed=42)
    
    # Start new game with $10 bet
    game = engine.start_new_game(10.0)
    print(f"Started game with ${game.bet_amount} bet")
    print(f"Game ID: {game.game_id}")
    print(f"Current round: {game.current_round.value}")
    print()
    
    # Round 1: Red or Black
    print("=== ROUND 1: RED OR BLACK ===")
    strategy = engine.get_strategy_recommendation(game)
    print(f"Strategy recommendation: {strategy.action}")
    print(f"Reasoning: {strategy.reasoning}")
    
    # Make guess
    is_correct, card, winnings = engine.make_guess(game, "red")
    print(f"Guessed: RED")
    print(f"Card drawn: {card} ({card.color.value})")
    print(f"Result: {'✅ CORRECT' if is_correct else '❌ WRONG'}")
    print(f"Winnings: ${winnings}")
    print(f"Game status: {game.status.value}")
    print()
    
    if game.status.value != 'active':
        print("Game ended!")
        return
    
    # Round 2: Higher or Lower
    print("=== ROUND 2: HIGHER OR LOWER ===")
    print(f"First card value: {game.cards_drawn[0].rank.value}")
    strategy = engine.get_strategy_recommendation(game)
    print(f"Strategy recommendation: {strategy.action}")
    print(f"Reasoning: {strategy.reasoning}")
    
    # Make guess based on strategy
    guess = "higher" if "higher" in strategy.action else "lower"
    is_correct, card, winnings = engine.make_guess(game, guess)
    print(f"Guessed: {guess.upper()}")
    print(f"Card drawn: {card} (value: {card.rank.value})")
    print(f"Result: {'✅ CORRECT' if is_correct else '❌ WRONG'}")
    print(f"Winnings: ${winnings}")
    print(f"Game status: {game.status.value}")
    print()
    
    if game.status.value != 'active':
        print("Game ended!")
        return
    
    # Round 3: Inside or Outside
    print("=== ROUND 3: INSIDE OR OUTSIDE ===")
    card1_val = game.cards_drawn[0].rank.value
    card2_val = game.cards_drawn[1].rank.value
    print(f"Range: {min(card1_val, card2_val)} - {max(card1_val, card2_val)}")
    strategy = engine.get_strategy_recommendation(game)
    print(f"Strategy recommendation: {strategy.action}")
    print(f"Reasoning: {strategy.reasoning}")
    
    # Check if we should cash out
    if "cash_out" in strategy.action:
        print("🏦 Strategy recommends CASH OUT!")
        winnings = engine.cash_out(game)
        print(f"Cashed out: ${winnings}")
        print(f"Game status: {game.status.value}")
        return
    
    # Make guess
    guess = "inside" if "inside" in strategy.action else "outside"
    is_correct, card, winnings = engine.make_guess(game, guess)
    print(f"Guessed: {guess.upper()}")
    print(f"Card drawn: {card} (value: {card.rank.value})")
    print(f"Result: {'✅ CORRECT' if is_correct else '❌ WRONG'}")
    print(f"Winnings: ${winnings}")
    print(f"Game status: {game.status.value}")
    print()
    
    if game.status.value != 'active':
        print("Game ended!")
        return
    
    # Round 4: Pick the Suit
    print("=== ROUND 4: PICK THE SUIT ===")
    used_suits = [card.suit.name.lower() for card in game.cards_drawn[:3]]
    print(f"Used suits: {used_suits}")
    strategy = engine.get_strategy_recommendation(game)
    print(f"Strategy recommendation: {strategy.action}")
    print(f"Reasoning: {strategy.reasoning}")
    
    # Make guess
    available_suits = ['hearts', 'diamonds', 'clubs', 'spades']
    guess_suit = None
    for suit in available_suits:
        if suit not in used_suits:
            guess_suit = suit
            break
    
    if guess_suit:
        is_correct, card, winnings = engine.make_guess(game, guess_suit)
        print(f"Guessed: {guess_suit.upper()}")
        print(f"Card drawn: {card}")
        print(f"Result: {'✅ CORRECT' if is_correct else '❌ WRONG'}")
        print(f"Final winnings: ${winnings}")
        print(f"Game status: {game.status.value}")
    else:
        print("❌ All suits used - should have cashed out!")
    
    print()
    print("=== GAME COMPLETE ===")
    if game.status.value == 'won':
        profit = game.current_winnings - game.bet_amount
        print(f"🎉 WON! Profit: ${profit}")
    elif game.status.value == 'lost':
        print(f"💔 LOST! Lost: ${game.bet_amount}")
    elif game.status.value == 'cashed_out':
        profit = game.current_winnings - game.bet_amount
        print(f"💰 CASHED OUT! Profit: ${profit}")


def test_strategy_system():
    """Test the strategy recommendation system"""
    print("\n🧠 Testing Strategy System 🧠\n")
    
    engine = CasinoRideTheBus(seed=123)
    
    # Test Round 2 strategies
    print("=== Round 2 Strategy Tests ===")
    
    # Low card (should pick higher)
    from casino_game import Card, Rank, Suit
    low_card = Card(Rank.THREE, Suit.HEARTS)  # Value 3
    strategy = engine._strategy_round2(low_card)
    print(f"Card 3: {strategy.action} (confidence: {strategy.confidence:.1%})")
    
    # Middle card (should cash out)
    mid_card = Card(Rank.EIGHT, Suit.CLUBS)  # Value 8
    strategy = engine._strategy_round2(mid_card)
    print(f"Card 8: {strategy.action} (confidence: {strategy.confidence:.1%})")
    
    # High card (should pick lower)
    high_card = Card(Rank.KING, Suit.SPADES)  # Value 13
    strategy = engine._strategy_round2(high_card)
    print(f"Card K: {strategy.action} (confidence: {strategy.confidence:.1%})")
    
    print("\n=== Round 3 Strategy Tests ===")
    
    # Pair (should pick outside)
    card1 = Card(Rank.SEVEN, Suit.HEARTS)
    card2 = Card(Rank.SEVEN, Suit.CLUBS)
    strategy = engine._strategy_round3(card1, card2)
    print(f"Pair 7-7: {strategy.action} (confidence: {strategy.confidence:.1%})")
    
    # Large gap (should pick inside)
    card1 = Card(Rank.ACE, Suit.HEARTS)  # 14
    card2 = Card(Rank.TWO, Suit.CLUBS)   # 2  
    strategy = engine._strategy_round3(card1, card2)
    gap = abs(card1.rank.value - card2.rank.value)
    print(f"A-2 gap ({gap}): {strategy.action} (confidence: {strategy.confidence:.1%})")
    
    # Medium gap (should cash out)
    card1 = Card(Rank.TEN, Suit.HEARTS)  # 10
    card2 = Card(Rank.FIVE, Suit.CLUBS)  # 5
    strategy = engine._strategy_round3(card1, card2)
    gap = abs(card1.rank.value - card2.rank.value)
    print(f"10-5 gap ({gap}): {strategy.action} (confidence: {strategy.confidence:.1%})")


def test_statistical_accuracy():
    """Test statistical calculations"""
    print("\n📊 Testing Statistical Accuracy 📊\n")
    
    # Test win probabilities for different scenarios
    wins = 0
    total_games = 1000
    
    print(f"Running {total_games} simulated Round 2 scenarios...")
    
    for i in range(total_games):
        engine = CasinoRideTheBus(seed=i)
        game = engine.start_new_game(10.0)
        
        # Round 1: Always guess red
        engine.make_guess(game, "red")
        
        if game.status.value == 'active':
            # Round 2: Use strategy
            strategy = engine.get_strategy_recommendation(game)
            if "higher" in strategy.action:
                is_correct, _, _ = engine.make_guess(game, "higher")
            elif "lower" in strategy.action:
                is_correct, _, _ = engine.make_guess(game, "lower")
            else:
                continue  # Skip cash out scenarios
            
            if is_correct:
                wins += 1
    
    win_rate = wins / total_games * 100
    print(f"Round 2 win rate with strategy: {win_rate:.1f}%")
    print("(Should be around 60-70% with optimal strategy)")


if __name__ == "__main__":
    test_full_game()
    test_strategy_system() 
    test_statistical_accuracy()