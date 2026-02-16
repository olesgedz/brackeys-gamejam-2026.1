# Gibberish TTS Generator

Generate mumbling pseudo-speech that preserves the rhythm and pauses of real English text. Perfect for game NPCs, background chatter, or alien languages.

## Installation

### Linux / WSL

```bash
sudo apt install espeak-ng ffmpeg
```

### Windows

**espeak-ng:**
- Download installer from [GitHub Releases](https://github.com/espeak-ng/espeak-ng/releases) (`espeak-ng-X.XX-x64.msi`)
- Or via package manager:
```powershell
# Chocolatey
choco install espeak-ng

# Winget
winget install espeak-ng.espeak-ng
```

**ffmpeg:**
```powershell
winget install ffmpeg
```

### macOS

```bash
brew install espeak-ng ffmpeg
```

## Quick Start

```bash
# List available presets
python gibberish_tts.py --list-presets

# Use a preset
python gibberish_tts.py "Hello, how are you?" output.wav --preset male1
python gibberish_tts.py "Hello, how are you?" output.wav --preset female2
python gibberish_tts.py "Hello, how are you?" output.wav --preset child1

# Without post-processing (raw espeak)
python gibberish_tts.py "Hello!" output.wav --preset male3 --no-fx
```

## Voice Presets

### 👨 Male Voices
| Preset | Description | Voice | Pitch | Speed |
|--------|-------------|-------|-------|-------|
| `male1` | Standard male | en+m1 | 20 | 135 |
| `male2` | Sharp male | en+m2 | 10 | 135 |
| `male3` | Deep male | en+m3 | 5 | 135 |
| `male4` | Raspy/old male | en+m7 | 1 | 130 |

### 👩 Female Voices
| Preset | Description | Voice | Pitch | Speed |
|--------|-------------|-------|-------|-------|
| `female1` | Standard female | en+f1 | 65 | 140 |
| `female2` | Soft female | en+f2 | 75 | 140 |
| `female3` | Low female | en+f3 | 70 | 135 |
| `female4` | High female | en+f4 | 80 | 145 |

### 👶 Child Voices
| Preset | Description | Voice | Pitch | Speed |
|--------|-------------|-------|-------|-------|
| `child1` | Child (high) | en+f4 | 99 | 150 |
| `child2` | Child (medium) | en+f3 | 95 | 155 |
| `child3` | Boy | en+m1 | 90 | 150 |
| `child4` | Small child | en+f5 | 99 | 160 |

## Post-Processing (Default FX)

All presets include warm analog-style post-processing:

| Effect | Value | Description |
|--------|-------|-------------|
| Pink noise | 0.1 | Adds grain/warmth |
| Highpass | 300 Hz | Removes rumble |
| Lowpass | 3000 Hz | Muffled/radio feel |
| EQ boost | +5dB @ 1kHz | Presence |
| Echo | 40+60 ms | Room ambience |

Disable with `--no-fx` for raw robotic output.

## All Parameters

```bash
python gibberish_tts.py "text" output.wav [options]

Options:
  --preset, -p    Voice preset (male1-4, female1-4, child1-4)
  --voice         espeak-ng voice (e.g., en+m3, en+f2)
  --pitch         Pitch 0-99 (lower = deeper)
  --speed         Words per minute
  --gap           Pause between words (×10ms)
  --no-fx         Disable post-processing
  --noise         Noise level (0-1), default 0.1
  --lowpass       Low-pass filter Hz, default 3000
  --highpass      High-pass filter Hz, default 300
  --show-gibberish  Print generated gibberish text
  --list-presets, -l  Show all presets
```

## Examples

```bash
# Deep mysterious NPC
python gibberish_tts.py "Welcome traveler." npc.wav --preset male4

# Excited child
python gibberish_tts.py "Oh wow look at that!" child.wav --preset child1

# Radio transmission
python gibberish_tts.py "Target acquired." radio.wav --preset male2 --lowpass 2000 --noise 0.2

# Clean female voice (no FX)
python gibberish_tts.py "Hello there." clean.wav --preset female1 --no-fx

# Custom voice
python gibberish_tts.py "Greetings." out.wav --voice en+m5 --pitch 30 --speed 120
```

## How It Works

1. **Text Analysis**: Splits input into words and punctuation
2. **Gibberish Generation**: Replaces words with random syllables (CV/CVC patterns)
3. **Pause Preservation**: Punctuation → pauses (`...` / `.....`)
4. **TTS**: espeak-ng generates raw speech
5. **Post-processing**: ffmpeg adds noise, EQ, echo for analog warmth

## Output

Generates 22050 Hz mono WAV files.

## License

MIT
