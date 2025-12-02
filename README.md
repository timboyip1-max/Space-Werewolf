# 🚀 Space Werewolf (5-Player Version)

A AI-powered multiplayer social deduction game inspired by *Among Us* and *Werewolf*, optimized for 5 players (3 Crewmates + 2 Impostors). Fixed role assignment issues and balanced gameplay to ensure fair competition between factions.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![API Support](https://img.shields.io/badge/DeepSeek-API%20v1-orange)

## 📖 What's This?

Space Werewolf is a text-based AI role-playing game where:
- 🛠️ **3 Crewmates** complete tasks, collect evidence, and eject Impostors
- 🕶️ **2 Impostors** sabotage the spaceship, frame Crewmates, and avoid detection
- 🤖 AI generates realistic speeches/defenses (powered by DeepSeek API or simulated dialogues)
- 🗳️ Strategic voting with 95% rational judgment + 5% random misjudgment (simulates human error)

## ✨ Core Features

1. **Fully Random Role Assignment**
   - 3 Crewmates selected from 5 unique roles (Engineer, Comms Officer, Navigator, Doctor, Technician)
   - 2 Impostors selected from 4 disguised roles (Supply Manager, Fake Navigator, Fake Doctor, Fake Technician)
   - No fixed role-player binding (solved previous role stagnation issue)

2. **Balanced Gameplay**
   - Impostors vote as a team to eliminate Crewmates
   - 60% chance to eject Crewmates in tie votes (balances Impostor survival)
   - 20% chance highest-suspicion player is innocent (adds uncertainty)

3. **Dual Mode Support**
   - 🌐 **API Mode**: Use DeepSeek API for dynamic AI dialogues (more realistic)
   - 🎮 **Simulation Mode**: Offline play with preset speeches/defenses (no API key required)

4. **Rich Game Mechanics**
   - Action report phase (2 rounds per voting cycle)
   - Emergency defense phase (targeted suspicion + evidence presentation)
   - Post-game review (view all player logs and real identities)

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- Required packages:
  ```bash
  pip install openai>=1.0.0  # For API integration
  pip install python-dotenv  # Optional: For .env file support
  ```

### 2. Configuration

#### Option A: Use .env File (Recommended)
1. Create a file named `DEEPSEEK_API_KEY.env` in the project root
2. Add your DeepSeek API credentials:
   ```env
   DEEPSEEK_API_KEY=your-api-key-here
   DEEPSEEK_BASE_URL=https://api.deepseek.com/v1  # Recommended endpoint
   DEEPSEEK_MODEL=deepseek-chat
   ```

#### Option B: No API Key (Simulation Mode)
- Skip API configuration – the game will automatically enable offline simulation with preset dialogues

### 3. Run the Game
```bash
python space_werewolf_5p_deepseek.py
```

## 📜 Game Rules

### Basic Setup
- Total Players: 5 (3 Crewmates + 2 Impostors)
- Game Rounds: 2 voting cycles (ensures definite outcome)
- Each voting cycle includes: Action Reports → Emergency Defense → Voting Ejection

### Victory Conditions

#### Crewmates Win If:
- All 2 Impostors are ejected within 2 voting rounds
- Remaining Crewmates > Remaining Impostors after 2 rounds
- No Impostors left alive

#### Impostors Win If:
- Remaining Impostors ≥ Remaining Crewmates (e.g., 2-2, 1-1)
- All Crewmates are eliminated
- Impostors maintain majority after 2 voting rounds

### Voting Rules
- 95% of votes target the highest-suspicion player
- 5% random vote chance (simulates human misjudgment)
- Eliminated players cannot participate in subsequent rounds
- Tie votes: Impostors have 60% acquittal chance

## 🎭 Role Introduction

### Crewmate Roles
| Role | Abilities | Key Evidence |
|------|-----------|--------------|
| Engineer Kai | Repair reactor/oxygen tank | Repair timestamps, wrench position |
| Comms Officer Lina | Monitor areas, transfer data | Communication logs, monitoring recordings |
| Navigator Ella | Calibrate course, track trajectories | Movement trajectory logs, data upload records |
| Doctor Mark | Physical exams, medical equipment | Vital sign data, exam records |
| Technician Lucy | Circuit inspection, equipment maintenance | Sensor logs, inspection reports |

### Impostor Roles
| Role | Disguise | Tactics |
|------|----------|---------|
| Vic | Supply Manager | Imitate Engineer, mutual vouch with Zoe |
| Zoe | Fake Navigator | Forge trajectory logs, shift blame to Vic |
| Jack | Fake Doctor | Forge medical records, mutual vouch with Lily |
| Lily | Fake Technician | Forge inspection reports, shift blame to Jack |

## 📂 Project Structure

```
space_werewolf_5p_deepseek.py
├── Config Class          # API + env configuration
├── GameConfig Class      # Game balance parameters (rounds, speech length, etc.)
├── AdvancedDeepSeekClient # AI dialogue generation + suspicion analysis
├── DebatablePlayer Class # Player role logic (speeches, defenses)
├── SpaceWerewolfGame Class # Core game flow (role assignment, rounds, voting)
└── main()                # Program entry point
```

## 🔧 Customization

Modify the `GameConfig` class to adjust gameplay parameters:
```python
class GameConfig:
    TEMPERATURE = 0.8          # AI creativity (0-1)
    RANDOM_VOTE_RATE = 0.05    # 5% random vote chance
    SPEECH_LENGTH_MIN = 12     # Minimum action report length
    DEBATE_LENGTH_MAX = 45     # Maximum defense length
    VOTE_ROUNDS = 2            # Total voting cycles
```

## ❗ Common Issues

### API Initialization Failed
- Check if your API key is valid and not expired
- Ensure `DEEPSEEK_BASE_URL` ends with `/v1`
- Verify network connectivity (API requires internet access)

### .env File Not Loaded
- Install `python-dotenv` (optional but recommended)
- Ensure the file is named `DEEPSEEK_API_KEY.env` and placed in the project root
- Check for typos in environment variable names (e.g., `DEEPSEEK_API_KEY` not `DEEPSEEK_KEY`)

### Game Crashes
- Ensure Python version ≥ 3.8
- Update dependencies: `pip install --upgrade openai python-dotenv`
- Check error logs for specific issues (stack trace printed in console)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## 📞 Support

If you encounter issues or have suggestions:
- Open a GitHub Issue
- Contact the maintainer for API-related questions

---

Made with ❤️ for social deduction game lovers!
