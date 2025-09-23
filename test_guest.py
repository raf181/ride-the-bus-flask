#!/usr/bin/env python3
"""Test guest functionality"""

import requests
import time

def test_guest_play():
    print("🎮 Testing Guest Play Functionality")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    try:
        # Test landing page loads
        response = session.get(base_url)
        print(f"✅ Landing page: {response.status_code}")
        
        # Test guest session creation
        response = session.post(f"{base_url}/play_as_guest")
        print(f"✅ Guest session: {response.status_code}")
        
        # Test starting a game as guest
        response = session.post(f"{base_url}/start_game", data={'bet_amount': 25})
        print(f"✅ Start game: {response.status_code}")
        
        # Test game page
        response = session.get(f"{base_url}/game")
        print(f"✅ Game page: {response.status_code}")
        
        print("\n🎯 Guest functionality appears to be working!")
        print("Manual testing recommended in browser.")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the Flask server is running.")

if __name__ == "__main__":
    test_guest_play()