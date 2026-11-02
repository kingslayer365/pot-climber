# Pot Climb (Python / Pygame)

## Play
    pip install -r requirements.txt
    python game.py

Modes: Climb Solo, Climb Online (room code), Fight vs Bot, Fight 2 Players (local).
Check install without a window: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python game.py --selftest`

## Online rooms (works over the internet)
1. On a PC/VPS with a public IP (or use port forwarding): `python server.py` (port 8765).
2. Everyone: Climb - Online Room, enter `server-ip:8765`, then the same 6-digit code
   (leave empty to create a new code and share it). 2-8 players, live ghosts, leaderboard, auto-reconnect.

## Android
Pygame desktop code does not run on a phone directly. Use Buildozer + pygame-ce/Kivy to package,
or ask for a Godot/Unity port. physics.py and server.py are reusable as-is.
