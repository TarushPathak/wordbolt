# WordBolt

**Personal Pattern Discovery Tool** — A targeted password wordlist generator that weaves personal information, leet-speak mutations, keyboard walks, and temporal patterns into probabilistically ranked candidate lists.

## Features

- **Pattern Weaver** — Combines names, nicknames, dates, places, and other personal seeds with common mutation patterns
- **Leet-Speak Engine** — Generates up to 16 leet variants per seed character
- **Multi-Profile Support** — Built-in profiles for `indian`, `corporate`, and `gamer` demographics
- **Probabilistic Scoring** — Ranks candidates by likelihood using a heuristic scoring engine
- **Multi-Format Output** — TXT, GZ, JSON, and Hashcat-ready formats
- **Multiprocessing** — Parallel seed processing for large workloads
- **Length Filtering** — Configurable min/max length constraints
- **Entropy Distribution** — Visual histogram of generated password lengths

## Dependencies

- Python 3.8+
- [SecLists](https://github.com/danielmiessler/SecLists) (optional, for keyboard walks and common credentials)

## Installation

```bash
git clone https://github.com/TarushPathak/wordbolt.git
cd wordbolt
pip3 install -r requirements.txt
```

For full functionality, clone SecLists:

```bash
git clone https://github.com/danielmiessler/SecLists.git ~/SecLists
```

## Usage

### Basic interactive mode

```bash
python3 wordbolt.py
```

Enter target details when prompted. Use `;` to separate multiple values and `NA` to skip a field (triggers Indian forename fallback).

### Command-line flags

```
SecLists Assets:
  -k, --keyboard-walks  Include keyboard walk patterns
  -c, --common-creds    Include common credential passwords
  --full                Include both -k and -c

Intensity:
  --lite                Lite mode: fewer mutations, range 1–20
  --aggressive          Aggressive mode: max mutations, range 1–1000

Length Filter:
  --min N               Minimum password length (default: 8)
  --max N               Maximum password length (default: 16)

Generation:
  --combo-depth N       Multi-seed combinations (e.g., 2)
  --profile {indian,corporate,gamer}
                        Predefined keyword/name profile
  --parallel            Use multiprocessing

Output:
  -o FILE               Save results to a file
  -f {txt,gz,json,hashcat}
                        Output format (default: txt)
  --preview N           Preview entries to display (default: 20)
```

### Examples

```bash
# Full mode with gamer profile, aggressive mutations
python3 wordbolt.py --full --profile gamer --aggressive -o output.txt

# Lite mode with keyboard walks
python3 wordbolt.py -k --lite --min 8 --max 12

# Parallel generation with multi-seed combos
python3 wordbolt.py --full --combo-depth 2 --parallel -f json -o results.json

# Compressed output ready for hashcat
python3 wordbolt.py -c --min 10 --max 20 -f hashcat -o wordlist.txt
```

## Output

WordBolt generates a probabilistically ranked wordlist. The scoring engine prioritizes:

1. Entries containing known seed values
2. Patterns ending with recent years
3. Common suffix patterns (`123`, `!`, `@`)
4. Capitalized and leet variants
5. Multi-seed combinations

The summary includes total entries, dedup savings, elapsed time, and a length-distribution histogram.

## License

MIT
