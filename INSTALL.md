# 🎰 Casino Ride the Bus - Installation Guide

Easy setup guide to get the Casino Ride the Bus game running on your computer!

## 📋 Prerequisites

Before you start, make sure you have:

- **Python 3.7+** installed on your computer
  - Download from [python.org](https://www.python.org/downloads/)
  - ✅ Check: Open terminal and type `python --version`

## 🚀 Quick Setup (3 steps!)

### 1️⃣ Download the Code

```bash
git clone https://github.com/raf181/ride-the-bus-flask.git
cd ride-the-bus-flask
```

### 2️⃣ Install Dependencies

```bash
pip install flask
```

*That's it! The game only needs Flask to run.*

### 3️⃣ Start the Game

```bash
python app.py
```

🎉 **Done!** Open your browser and go to: `http://localhost:5000`

## 🎮 How to Play

1. **Register** a new account or **Play as Guest**
2. **Choose your bet** amount (guests start with $1000)
3. **Play 4 rounds** of card guessing:
   - **Round 1**: Red or Black? (2x multiplier)
   - **Round 2**: Higher or Lower? (2x multiplier)  
   - **Round 3**: Inside or Outside? (3x multiplier)
   - **Round 4**: Which suit? (4x multiplier)
4. **Cash out** anytime after Round 1 to keep your winnings!

## 🛠️ Troubleshooting

### Problem: "Flask not found"
**Solution:** Install Flask
```bash
pip install flask
```

### Problem: "Port already in use"
**Solution:** The game runs on port 5000. If busy, kill other processes or change the port in `app.py`:
```python
app.run(debug=True, port=5001)  # Change to 5001
```

### Problem: "Permission denied"
**Solution:** Make sure you're in the right folder:
```bash
cd ride-the-bus-flask
ls  # Should show app.py, casino_game.py, etc.
```

## 📁 Project Structure
```
ride-the-bus-flask/
├── app.py              # Main Flask web server
├── casino_game.py      # Game logic & rules
├── user_manager.py     # User accounts & database
├── templates/          # Web pages (HTML)
├── static/            # Styles & scripts (CSS/JS)
└── users.db           # Database (created automatically)
```

## 🔧 Advanced Options

### Development Mode (auto-restart on changes)
```bash
python app.py
# Already enabled in the code!
```

### Run Tests
```bash
python test_casino.py
```

### Custom Database Location
Edit `user_manager.py` and change the database path if needed.

## 💡 Features

- ✅ **Guest Play** - No registration required
- ✅ **User Accounts** - Save your progress and bankroll  
- ✅ **Daily Bonuses** - Get free money each day
- ✅ **Strategy Tips** - Built-in AI recommendations
- ✅ **Game History** - Track your wins and losses
- ✅ **Mobile Friendly** - Play on phone or computer

## 🎯 Game Tips

- **Round 2**: Cash out with middle cards (6-10)
- **Round 3**: Pick "Outside" for pairs and connecting cards
- **Round 4**: All suits have equal 25% chance
- **Strategy**: Use the built-in recommendations for optimal play!

## 📞 Need Help?

- Check the terminal output for error messages
- Make sure you're using Python 3.7 or newer
- Verify Flask is installed: `pip show flask`

---

**Have fun and good luck! 🍀**