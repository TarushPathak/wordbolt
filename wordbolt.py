#!/usr/bin/env python3
"""
WordBolt v8.0 — Personal Pattern Discovery Tool
"""

__version__ = "8.0.0"

import argparse
import gzip
import itertools
import json
import multiprocessing
import os
import random
import sys
from collections import defaultdict
from datetime import datetime


# ─────────────────────────────────────────────
# UI & AESTHETICS
# ─────────────────────────────────────────────
class Colors:
    GREEN  = '\033[92m'
    GREY   = '\033[90m'
    WHITE  = '\033[97m'
    CYAN   = '\033[96m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def c(color, text):
    return f"{color}{text}{Colors.END}"

BANNER = rf"""
{c(Colors.GREEN, '  //-- W O R D B O L T --////////////////////////')}
{c(Colors.GREEN, '      _    _               _ ____       _ _       ')}
{c(Colors.GREEN, '     | |  | |             | |  _ \\     | | |      ')}
{c(Colors.GREEN, '     | |  | | ___  _ __ __| | |_) | ___| | |_     ')}
{c(Colors.GREEN, '     | |/\\| |/ _ \\| \'__/ _` |  _ < / _ \\ | __|    ')}
{c(Colors.GREEN, '     \\  /\\  / (_) | | | (_| | |_) | (_) | | |_    ')}
{c(Colors.GREEN, '      \\/  \\/ \\___/|_|  \\__,_|____/ \\___/|_|\\__|   ')}
{c(Colors.GREEN, f'  //////////////////////////////////////// v{__version__}--//')}

    {c(Colors.GREY, '--------------------------------------------------')}
    {c(Colors.WHITE, f'[ TYPE: Pattern Weaver ]      [ VERSION: {__version__}-LTD ]')}
    {c(Colors.WHITE, '[ AUTH: TARUSH ADESH PATHAK ] [ SOURCE: SECLISTS ]')}
    {c(Colors.GREY, '--------------------------------------------------')}
"""

EPILOG = f"""
{Colors.CYAN}Examples:{Colors.END}
  wordbolt.py --full -o dump.txt
  wordbolt.py -k --min 6 --max 20
  wordbolt.py -c --profile indian --aggressive -o out.txt
  wordbolt.py --full --combo-depth 2 -f gz -o results.gz
  wordbolt.py --lite --min 8 --max 12 -o quick.txt

{Colors.YELLOW}Profiles:{Colors.END}  indian | corporate | gamer
{Colors.YELLOW}Formats:{Colors.END}   txt | gz | json | hashcat
"""


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SECLISTS_BASE = os.path.expanduser("~/SecLists")

PROFILES = {
    "indian": {
        "forenames":  "Usernames/Names/forenames-india-top1000.txt",
        "surnames":   "Usernames/Names/surnames-india-top1000.txt",
        "keywords":   ["india", "bharat", "desi", "hindi", "mumbai", "delhi"],
    },
    "corporate": {
        "keywords":   ["admin", "welcome", "letmein", "company", "secure",
                       "password", "office", "work", "corp", "login"],
    },
    "gamer": {
        "keywords":   ["player", "gamer", "noob", "pro", "clan", "guild",
                       "level", "boss", "hack", "cheat"],
    },
}

SYMBOLS = ['!', '@', '#', '$', '%', '&', '*']

MUTATION_SUFFIXES = {
    "common":     ["123", "1234", "12345", "123456", "1!", "!1", "01", "00"],
    "caps_sym":   ["!",   "@",   "#",    "$",    "!@#"],
    "years":      [],
}

LEET_MAP = {
    'a': ['a', '@', '4'],
    'b': ['b', '8', '6'],
    'e': ['e', '3'],
    'g': ['g', '9'],
    'i': ['i', '1', '!'],
    'o': ['o', '0'],
    's': ['s', '$', '5'],
    't': ['t', '7'],
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def load_list(rel_path):
    path = os.path.join(SECLISTS_BASE, rel_path)
    if os.path.exists(path):
        with open(path, 'r', errors='ignore') as f:
            return [ln.strip() for ln in f if ln.strip()]
    return []


def get_leet_variants(word, cap=8):
    options = [LEET_MAP.get(ch.lower(), [ch]) for ch in word]
    return [''.join(combo) for combo in list(itertools.product(*options))[:cap]]


def normalize_seeds(seeds):
    seen = set()
    out  = []
    for s in seeds:
        sl = s.lower().strip()
        if sl and sl not in seen:
            seen.add(sl)
            out.append(sl)
    return out


def entropy_label(length):
    if length < 8:   return c(Colors.RED,    "WEAK")
    if length < 10:  return c(Colors.YELLOW, "FAIR")
    if length < 13:  return c(Colors.GREEN,  "GOOD")
    return c(Colors.CYAN,  "STRONG")


def build_year_list():
    now = datetime.now().year
    years = []
    for y in range(now - 10, now + 1):
        years.append(str(y))
        years.append(str(y)[2:])
    return years


def print_summary(total_raw, total_unique, before_filter, elapsed):
    reduction = ((total_raw - total_unique) / max(total_raw, 1)) * 100
    print(f"\n{c(Colors.CYAN, '─' * 48)}")
    print(f"  {c(Colors.BOLD, 'WORDLIST SUMMARY')}")
    print(f"{c(Colors.CYAN, '─' * 48)}")
    print(f"  Generated (raw)   : {c(Colors.WHITE,  str(total_raw))}")
    print(f"  After dedup       : {c(Colors.WHITE,  str(total_unique))}")
    print(f"  After len filter  : {c(Colors.GREEN,  str(before_filter))}")
    print(f"  Duplicate savings : {c(Colors.YELLOW, f'{reduction:.1f}%')}")
    print(f"  Time elapsed      : {c(Colors.GREY,   f'{elapsed:.2f}s')}")
    print(f"{c(Colors.CYAN, '─' * 48)}")


# ─────────────────────────────────────────────
# GENERATION WORKER (for multiprocessing)
# ─────────────────────────────────────────────
def generate_for_seed(args_tuple):
    seed, date_seeds, intensity, combo_seeds = args_tuple
    local = set()
    variants  = get_leet_variants(seed, cap=16 if intensity == "aggressive" else 8)

    for v in variants:
        bases = [v, v.capitalize(), v.upper(), v.title()]
        for b in bases:
            local.add(b)

            # ── Numerical brute range ──────────────────────────────
            limit = 1000 if intensity == "aggressive" else (100 if intensity == "normal" else 20)
            for i in range(1, limit + 1):
                local.add(f"{b}{i}")
                if i < 100:
                    for sym in SYMBOLS:
                        local.add(f"{b}{sym}{i}")
                        local.add(f"{sym}{b}{i}")

            # ── Common suffixes ────────────────────────────────────
            for suf in MUTATION_SUFFIXES["common"]:
                local.add(f"{b}{suf}")

            # ── Symbol suffixes ────────────────────────────────────
            for sym in MUTATION_SUFFIXES["caps_sym"]:
                local.add(f"{b}{sym}")
                local.add(f"{sym}{b}")

            # ── Year integration ───────────────────────────────────
            for y in MUTATION_SUFFIXES["years"]:
                local.add(f"{b}{y}")
                for sym in SYMBOLS[:4]:
                    local.add(f"{b}{sym}{y}")

            # ── Temporal (date fragments) ──────────────────────────
            for d in date_seeds:
                local.add(f"{b}{d}")
                for sym in SYMBOLS[:4]:
                    local.add(f"{b}{sym}{d}")

    # ── Multi-seed combinations ────────────────────────────────────
    if combo_seeds and len(combo_seeds) >= 2:
        for other in random.sample(combo_seeds, min(len(combo_seeds), 5)):
            if other != seed:
                local.add(f"{seed}{other}")
                local.add(f"{other}{seed}")
                local.add(f"{seed}@{other}")
                local.add(f"{seed}_{other}")

    return local


# ─────────────────────────────────────────────
# SCORING / PROBABILISTIC RANKING
# ─────────────────────────────────────────────
def score_word(word, seeds, years):
    score = 0
    wl    = word.lower()

    # Seed present?
    for s in seeds:
        if s in wl:
            score += 90
            if wl.startswith(s):
                score += 10

    # Ends with recent year?
    for y in years:
        if wl.endswith(y):
            score += 80

    # Ends with 123 / common patterns
    for suf in ["123", "1234", "!",  "@", "#"]:
        if wl.endswith(suf):
            score += 75

    # Capitalization present
    if word[0].isupper():
        score += 20

    # Symbol present
    if any(c in word for c in SYMBOLS):
        score += 15

    # Leet chars
    if any(c in word for c in ['@', '4', '3', '1', '0', '$', '5', '7']):
        score += 10

    # Penalise very short or very long
    if len(word) < 9 or len(word) > 14:
        score -= 5

    return score


# ─────────────────────────────────────────────
# OUTPUT WRITERS
# ─────────────────────────────────────────────
def write_output(results, path, fmt, meta):
    try:
        header_lines = [
            f"# Generated by WordBolt v8.0",
            f"# Entries  : {meta['entries']}",
            f"# Date     : {meta['date']}",
            f"# Seeds    : {meta['seeds']}",
            f"# Intensity: {meta['intensity']}",
            "",
        ]

        if fmt == "gz":
            with gzip.open(path, 'wt', encoding='utf-8') as f:
                f.write("\n".join(header_lines) + "\n".join(results))

        elif fmt == "json":
            payload = {
                "meta":    meta,
                "entries": results,
            }
            with open(path, 'w') as f:
                json.dump(payload, f, indent=2)

        elif fmt == "hashcat":
            with open(path, 'w') as f:
                f.write("\n".join(results))

        else:  # txt (default)
            with open(path, 'w') as f:
                f.write("\n".join(header_lines) + "\n".join(results))

        print(f"\n{c(Colors.GREEN, f'[✓] Saved → {path}  ({fmt.upper()})')}")

    except Exception as e:
        print(c(Colors.RED, f"[!] Write Error: {e}"))


# ─────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(
        prog="wordbolt",
        description="WordBolt v8.0 — Personal Pattern Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )

    # SecLists asset flags
    asset = parser.add_argument_group("SecLists Assets")
    asset.add_argument("-k", "--keyboard-walks", action="store_true",
                       help="Include keyboard walk patterns")
    asset.add_argument("-c", "--common-creds",   action="store_true",
                       help="Include common credential passwords")
    asset.add_argument("--full",                 action="store_true",
                       help="Include both -k and -c")

    # Intensity
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--lite",       action="store_true",
                      help="Lite mode: fewer mutations, range 1–20")
    mode.add_argument("--aggressive", action="store_true",
                      help="Aggressive mode: maximum mutations, range 1–1000")

    # Length filter
    filt = parser.add_argument_group("Length Filter")
    filt.add_argument("--min", type=int, default=8,  metavar="N",
                      help="Minimum password length (default: 8)")
    filt.add_argument("--max", type=int, default=16, metavar="N",
                      help="Maximum password length (default: 16)")

    # Combo
    parser.add_argument("--combo-depth", type=int, default=0, metavar="N",
                        help="Enable multi-seed combinations (e.g. --combo-depth 2)")

    # Profile
    parser.add_argument("--profile", choices=list(PROFILES.keys()),
                        help="Load a predefined keyword/name profile")

    # Parallel
    parser.add_argument("--parallel", action="store_true",
                        help="Use multiprocessing for faster generation")

    # Output
    out = parser.add_argument_group("Output")
    out.add_argument("-o", "--output", metavar="FILE",
                     help="Save results to a file")
    out.add_argument("-f", "--format",
                     choices=["txt", "gz", "json", "hashcat"],
                     default="txt", metavar="FMT",
                     help="Output format: txt (default), gz, json, hashcat")
    out.add_argument("--preview", type=int, default=20, metavar="N",
                     help="Number of preview entries to display (default: 20)")

    return parser


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = build_parser()
    args   = parser.parse_args()

    print(BANNER)

    # ── Resolve intensity ──────────────────────────────────────────
    if args.lite:
        intensity = "lite"
    elif args.aggressive:
        intensity = "aggressive"
    else:
        intensity = "normal"

    print(c(Colors.GREY, f"  Mode: {intensity.upper()}  |  "
                         f"Length: {args.min}–{args.max}  |  "
                         f"Combo-depth: {args.combo_depth}\n"))

    # ── Collect user input ─────────────────────────────────────────
    print(c(Colors.BOLD, "Enter target details (';' to separate, 'NA' to skip):"))
    try:
        fields = {
            "Names":     input(c(Colors.GREEN, "Names: ")),
            "Nicknames": input(c(Colors.GREEN, "Nicknames: ")),
            "Pets":      input(c(Colors.GREEN, "Pet Names: ")),
            "Dates":     input(c(Colors.GREEN, "Dates (dd/mm/yyyy): ")),
            "Places":    input(c(Colors.GREEN, "Places & Locations: ")),
            "Phone":     input(c(Colors.GREEN, "Phone Numbers: ")),
            "Favs":      input(c(Colors.GREEN, "Favorites: ")),
            "Other":     input(c(Colors.GREEN, "Other Strings: ")),
        }
    except KeyboardInterrupt:
        print(c(Colors.RED, "\n\n[!] Interrupted by user. Exiting."))
        sys.exit(0)

    seeds = []

    # ── Indian Forenames Fallback ──────────────────────────────────
    if fields["Names"].upper() == "NA" or fields["Nicknames"].upper() == "NA":
        print(c(Colors.YELLOW, "\n[*] Triggering Indian Forenames Fallback..."))
        indian_names = load_list("Usernames/Names/forenames-india-top1000.txt")
        if indian_names:
            seeds.extend(random.sample(indian_names, 40))
        else:
            print(c(Colors.RED, "[!] Could not find forenames list in SecLists."))

    for key, val in fields.items():
        if val.upper() != "NA" and key != "Dates":
            seeds.extend([s.strip() for s in val.split(';') if s.strip()])

    # ── Profile Injection ──────────────────────────────────────────
    if args.profile:
        prof = PROFILES[args.profile]
        print(c(Colors.YELLOW, f"\n[*] Loading profile: {args.profile}"))
        if "keywords" in prof:
            seeds.extend(prof["keywords"])
        if "forenames" in prof:
            names = load_list(prof["forenames"])
            if names:
                seeds.extend(random.sample(names, min(30, len(names))))
        if "surnames" in prof:
            surnames = load_list(prof["surnames"])
            if surnames:
                seeds.extend(random.sample(surnames, min(20, len(surnames))))

    seeds = normalize_seeds(seeds)

    # ── Date Processing ────────────────────────────────────────────
    date_seeds = set()
    if fields["Dates"].upper() != "NA":
        for d in fields["Dates"].split(';'):
            try:
                dt = datetime.strptime(d.strip(), "%d/%m/%Y")
                date_seeds.update([
                    dt.strftime("%Y"),
                    dt.strftime("%y"),
                    dt.strftime("%d%m"),
                    dt.strftime("%m%Y"),
                    dt.strftime("%d%m%Y"),
                ])
            except ValueError:
                continue

    # ── Auto Year Seeds ────────────────────────────────────────────
    MUTATION_SUFFIXES["years"] = build_year_list()

    # ── SecLists Assets ────────────────────────────────────────────
    if args.full:
        args.keyboard_walks = True
        args.common_creds   = True

    final_wordlist = set()

    if args.keyboard_walks:
        print(c(Colors.YELLOW, "[*] Importing Keyboard Walks..."))
        walks = load_list("Passwords/Keyboard-Walks/walk-the-line.txt")
        final_wordlist.update(walks[:300])
        print(c(Colors.GREY,   f"    → {len(walks[:300])} entries loaded"))

    if args.common_creds:
        print(c(Colors.YELLOW, "[*] Importing Common Credentials..."))
        common = load_list("Passwords/Common-Credentials/10k-most-common.txt")
        final_wordlist.update(common[:300])
        print(c(Colors.GREY,   f"    → {len(common[:300])} entries loaded"))

    raw_count_before = len(final_wordlist)

    # ── Core Pattern Weaver ────────────────────────────────────────
    print(c(Colors.GREEN, f"\n[+] Weaving patterns for {len(seeds)} seeds..."))
    t_start = datetime.now()

    combo_seeds = seeds if args.combo_depth >= 2 else []

    tasks = [
        (seed, date_seeds, intensity, combo_seeds)
        for seed in seeds
    ]

    if args.parallel and len(tasks) > 4:
        print(c(Colors.YELLOW, "[*] Using multiprocessing..."))
        with multiprocessing.Pool() as pool:
            results_list = pool.map(generate_for_seed, tasks)
        for r in results_list:
            final_wordlist.update(r)
    else:
        for idx, task in enumerate(tasks, 1):
            sys.stdout.write(
                f"\r{c(Colors.YELLOW, '[*]')} Processing seed "
                f"{c(Colors.WHITE, str(idx))}/{len(tasks)}: "
                f"{c(Colors.CYAN, task[0][:20]):<22}"
            )
            sys.stdout.flush()
            final_wordlist.update(generate_for_seed(task))

    print()

    raw_total   = len(final_wordlist)
    t_elapsed   = (datetime.now() - t_start).total_seconds()

    # ── Length Filter ──────────────────────────────────────────────
    filtered = [w for w in final_wordlist if args.min <= len(w) <= args.max]

    # ── Probabilistic Ranking ──────────────────────────────────────
    score_cache = {}
    year_list   = [y for y in MUTATION_SUFFIXES["years"] if len(y) == 4]

    def get_score(word):
        if word not in score_cache:
            score_cache[word] = score_word(word, seeds, year_list)
        return score_cache[word]

    results = sorted(filtered, key=get_score, reverse=True)

    # ── Entropy Distribution ───────────────────────────────────────
    length_dist = defaultdict(int)
    for w in results:
        length_dist[len(w)] += 1

    # ── Summary ───────────────────────────────────────────────────
    print_summary(
        total_raw    = raw_total + raw_count_before,
        total_unique = raw_total,
        before_filter= len(results),
        elapsed      = t_elapsed,
    )

    print(f"\n  {c(Colors.BOLD, 'Length Distribution:')}")
    for length in sorted(length_dist):
        bar = '█' * min(40, length_dist[length] // max(1, len(results) // 40))
        print(f"   {length:>2}  {bar} {length_dist[length]}  {entropy_label(length)}")

    print(f"\n{c(Colors.GREY, f'Preview (top {args.preview} by score):')}")
    for r in results[:args.preview]:
        print(f"   {c(Colors.CYAN, '›')} {r}")

    # ── Save ──────────────────────────────────────────────────────
    if args.output:
        meta = {
            "entries":   len(results),
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "seeds":     ", ".join(seeds[:10]),
            "intensity": intensity,
            "min_len":   args.min,
            "max_len":   args.max,
        }
        write_output(results, args.output, args.format, meta)
    else:
        print(c(Colors.GREY, "\n[i] Use -o <file> to save. Use -f to choose format."))


if __name__ == "__main__":
    main()
