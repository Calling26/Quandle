#!/usr/bin/env python3
"""
QUANDLE - A Quantum Wordle Variant
====================================
The target word exists in superposition of TWO words.
Your observations will collapse the wave function.

Requires: pip install rich
Usage:    python quandle.py [--dev]
"""

import argparse
import random
import sys
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set, Dict
from pathlib import Path

# Fix Windows console encoding before anything else
if sys.platform == "win32":
    os.system("")  # Enable VT100 escape sequences on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

try:
    import urllib.request
    import urllib.error
except ImportError:
    urllib = None  # type: ignore

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.rule import Rule
    from rich import box
    from rich.style import Style
except ImportError:
    print("\n  Quandle requires the 'rich' library for terminal rendering.")
    print("  Install it with:  pip install rich\n")
    sys.exit(1)


# ===================================================================
#  CONSTANTS & CONFIGURATION
# ===================================================================

WORD_LENGTH = 5

WORD_LIST_URLS = [
    "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
]

CACHE_FILE = Path(__file__).parent / ".quandle_wordcache.txt"

# Tile rendering styles (background colors for the letter tiles)
TILE_STYLES = {
    "green":  Style(color="white", bgcolor="green", bold=True),
    "yellow": Style(color="black", bgcolor="yellow", bold=True),
    "purple": Style(color="white", bgcolor="magenta", bold=True),
    "gray":   Style(color="white", bgcolor="color(238)", bold=True),
}

# Keyboard letter color styles
KEY_STYLES = {
    "green":   Style(color="green", bold=True),
    "yellow":  Style(color="yellow", bold=True),
    "purple":  Style(color="magenta", bold=True),
    "gray":    Style(color="color(240)", dim=True, strike=True),
    "unknown": Style(color="white"),
}

# ASCII-safe symbols used throughout the UI (no emoji)
SYM_ATOM     = "[*]"
SYM_BANG     = "[!]"
SYM_SPIRAL   = "[~]"
SYM_SPARK    = ">>>"
SYM_CHECK    = "[OK]"
SYM_WARN     = "/!\\"
SYM_STAR     = "***"
SYM_WRENCH   = "[#]"
SYM_WAVE     = "~~~"

# Curated fallback word list -- verified 5-letter isograms.
# Used if the online word list download fails.
FALLBACK_WORDS = """
about adept agile anger angle ankle arise atone audio baker basin batch
beach being black blade blame blank blaze blend blind block blond blunt
board boned borne bound brain brand brave bread brick bride bring broad
broke brown brunt brush build built burnt cable camel cargo chain chair
chalk champ charm chase cheap chest child china choir choke chord cider
claim clamp clean clear climb cling cloak clone cloth cloud clown coast
cobra comet coral count court cover craft crane crash crest crime crisp
crowd crown crush crypt curve dance dealt demon depot depth diner doing
doubt dough draft drain drank drape drawn dream drink drive drone drunk
dwarf dying early earth eight elbow empty enjoy entry equal equip ethic
exist extra fable fairy faith fault fibre field fiery fight filth final
fixed flame flair flesh fling float flock flora fluid focal forge forth
found frame frank fraud fresh fried frost froze fruit fungi ghost glare
gleam glide globe glove glyph goats graft grain grand grant graph grasp
grave great grind gripe groin grope grove grown guide guild guilt guise
handy harsh hasty haunt haven heard heart heavy hinge horse hotel hound
house human humid hurts hyper ideal image ivory jewel joint judge juice
jumbo kebab knife knelt laced laden large laser latch later laugh layer
leapt leash ledge lemon light liken liner lofty logic lousy lucid lumps
lunch lured lying lyric magic major maple march mason match mayor meals
meant medal mercy merit micro might miner minus model money month moral
motel mould mount mourn mouse mouth moved mover music naive nerve night
noble noise north noted novel nurse ocean omega onset optic orbit other
ought outer owner oxide paint panel panic parse party paste patch pause
peach phase piano picky pilot pinch pixel place plaid plain plane plank
plant plate plaza plead plods plumb plume poker point poise polar pound
power prawn pride prime print prior prize probe prong prone proud prove
prude psalm pulse punch purge quail qualm quart query quest quick quiet
quirk quota quote quilt radio raise range rapid ratio reach react ready
realm reign relax remit renal repay reply ridge right rigid risky rival
river roast robin rocky rogue rough round route royal rugby ruins ruled
rumba saint satin savor scale scamp scare scene scent scone scope score
scout sedan setup shade shake shame shape share shark sharp shave shelf
shift shine shire shirt shock shore short shout shove shown shrub shrug
sight since skate skirt slain slate slave slice slide slime slope sloth
smart smear smile smith smoke snack snail snake snare snipe snore solar
solid solve sonic south space spare spark spawn speak spear speck spend
spent spice spike spine spite split spoke spore sport spray squad stack
stage staid stain stake stale stalk stamp stand stank stare stark steam
stern sting stock stoke stomp stone store storm story stove strap straw
stray strip strum strut stuck study stump stung style sugar surge swamp
swear swept swift swing swipe swirl swore sworn swung synth table tango
teach theft thick thing think third thorn threw throw thump tiger timed
tired titan token total touch tough towel tower toxic trace track trade
trail train tramp trash trend trial trick trims trout truck truly trump
trunk trust tuber tumor tuned turbo twice twirl typed ultra under unify
union unite until upset urban using vague valid value vault video vigor
vinyl viola viper virus vital vocal vodka voice voter vouch wager waste
watch water waved whack whale wheat whelk whine whirl white widen wider
witch woman world worth would wound wrath write wrong wrote yacht yield
young youth zebra zonal
""".split()


# ===================================================================
#  WORD LIST MANAGEMENT
# ===================================================================

def is_isogram(word: str) -> bool:
    """Check if a word has no repeating letters."""
    return len(set(word)) == len(word)


def load_dictionary(console: Console) -> Set[str]:
    """
    Load and filter a word list to strictly contain 5-letter isograms.

    Strategy:
      1. Check for a cached isogram file from a previous run.
      2. Download a comprehensive English word list and filter it.
      3. Fall back to the curated built-in list.

    All paths run through the isogram filter for safety.
    """
    # 1. Try cached file
    if CACHE_FILE.exists():
        try:
            words = {
                w.strip().lower()
                for w in CACHE_FILE.read_text(encoding="utf-8").splitlines()
                if w.strip()
            }
            if len(words) > 100:
                console.print(f"  [dim]Loaded {len(words):,} isograms from cache[/]")
                return words
        except Exception:
            pass

    # 2. Try downloading
    raw_words: Set[str] = set()
    if urllib is not None:
        for url in WORD_LIST_URLS:
            try:
                console.print("  [dim]Downloading word list...[/]")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Quandle/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    text = resp.read().decode("utf-8", errors="ignore")
                    for line in text.splitlines():
                        w = line.strip().lower()
                        if (
                            len(w) == WORD_LENGTH
                            and w.isalpha()
                            and is_isogram(w)
                        ):
                            raw_words.add(w)
                if len(raw_words) > 100:
                    break
            except Exception as exc:
                console.print(f"  [dim yellow]Download failed ({exc})[/]")

    # 3. Fallback to curated built-in list
    if len(raw_words) < 100:
        console.print("  [dim]Using built-in word list[/]")
        raw_words = {
            w
            for w in FALLBACK_WORDS
            if len(w) == WORD_LENGTH and w.isalpha() and is_isogram(w)
        }

    # Cache for next launch
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            "\n".join(sorted(raw_words)), encoding="utf-8"
        )
    except Exception:
        pass

    console.print(f"  [dim]Dictionary ready: {len(raw_words):,} valid isograms[/]")
    return raw_words


# ===================================================================
#  DATA TYPES
# ===================================================================

class Phase(Enum):
    """The three quantum phases of a Quandle game."""

    SUPERPOSITION = "superposition"  # Two entangled target words
    COLLAPSED = "collapsed"          # Wave function collapsed to one word
    ALTERNATE = "alternate"          # First word solved; now solving the other


@dataclass
class TileResult:
    """Evaluation result for a single letter position."""

    letter: str
    color: str  # "green" | "yellow" | "purple" | "gray"


@dataclass
class GuessRecord:
    """A single guess stored in the game history."""

    word: str
    tiles: List[TileResult]
    phase: Phase
    guess_number: int
    note: str = ""  # "COLLAPSE", "COLLAPSE+SOLVE", "SOLVED", "VICTORY"


# ===================================================================
#  TILE EVALUATION LOGIC
# ===================================================================

def evaluate_superposition(
    guess: str, word_a: str, word_b: str
) -> Tuple[List[TileResult], Optional[str]]:
    """
    Evaluate a guess against TWO target words (Phase 1 - Superposition).

    Quantum Tile Rules:
    ---------------------------------------------------------------
    Color   | Condition                            | Collapse?
    --------|--------------------------------------|----------
    Green   | Correct pos for BOTH words (shared)  | No
    Green   | Correct pos for ONE word (unique)    | YES -> that word
    Yellow  | In BOTH words, wrong position        | No
    Purple  | In ONE word only, wrong position     | No
    Gray    | Not in either word                   | No
    ---------------------------------------------------------------

    The Paradox Rule (Double Unique Green):
    If unique greens point to BOTH words simultaneously, they create
    a quantum paradox and cancel each other out.  The superposition
    is preserved (no collapse), and those conflicting green tiles are
    downgraded to Purple -- the letter still belongs exclusively to
    one reality, but its positional certainty is revoked.

    Returns:
        tiles: List of TileResult for each position
        collapse_target: 'A', 'B', or None
    """
    tiles: List[TileResult] = []
    collapse_targets: Set[str] = set()
    # Track indices of unique-green tiles so they can be recolored on paradox
    unique_green_indices: List[int] = []

    for i in range(WORD_LENGTH):
        letter = guess[i]

        # --- Positional matches (green checks) ---
        in_pos_a = letter == word_a[i]
        in_pos_b = letter == word_b[i]

        # --- Presence checks (yellow / purple) ---
        in_word_a = letter in word_a
        in_word_b = letter in word_b

        if in_pos_a and in_pos_b:
            # SHARED GREEN - correct for both words, no collapse
            tiles.append(TileResult(letter, "green"))

        elif in_pos_a:
            # UNIQUE GREEN for Word A - tentatively green, may be paradoxed
            tiles.append(TileResult(letter, "green"))
            collapse_targets.add("A")
            unique_green_indices.append(i)

        elif in_pos_b:
            # UNIQUE GREEN for Word B - tentatively green, may be paradoxed
            tiles.append(TileResult(letter, "green"))
            collapse_targets.add("B")
            unique_green_indices.append(i)

        elif in_word_a and in_word_b:
            # YELLOW - letter exists in both words at wrong positions
            tiles.append(TileResult(letter, "yellow"))

        elif in_word_a or in_word_b:
            # PURPLE - letter exists in only one word, wrong position
            tiles.append(TileResult(letter, "purple"))

        else:
            # GRAY - letter is in neither word
            tiles.append(TileResult(letter, "gray"))

    # Resolve collapse:
    # - Single unique green word -> collapse to that word.
    # - Paradox Rule: double unique green (both A and B) -> cancel collapse.
    #   Recolor the conflicting unique greens to purple (the letter is still
    #   exclusively in one word, but positional certainty is revoked).
    if len(collapse_targets) == 1:
        return tiles, collapse_targets.pop()
    elif len(collapse_targets) == 2:
        for idx in unique_green_indices:
            tiles[idx] = TileResult(tiles[idx].letter, "purple")
        return tiles, None
    return tiles, None


def evaluate_standard(guess: str, target: str) -> List[TileResult]:
    """
    Standard Wordle evaluation against a single target word.
    Used in Phase 2 (Collapsed) and Phase 3 (Alternate Reality).

    Since all words in the dictionary are isograms, duplicate-letter
    handling is unnecessary - every letter appears at most once.
    """
    tiles: List[TileResult] = []

    for i in range(WORD_LENGTH):
        letter = guess[i]
        if letter == target[i]:
            tiles.append(TileResult(letter, "green"))
        elif letter in target:
            tiles.append(TileResult(letter, "yellow"))
        else:
            tiles.append(TileResult(letter, "gray"))

    return tiles


# ===================================================================
#  ENTANGLED PAIR SELECTION (Guaranteed Entanglement)
# ===================================================================

def find_entangled_pair(
    guess: str, dictionary: Set[str]
) -> Tuple[str, str]:
    """
    After the player submits Guess 1, dynamically choose Word A and
    Word B such that NO letter in the guess occupies the correct
    position in either word.  This guarantees no green tiles (neither
    shared nor unique) on the very first guess, preventing a lucky
    first-turn collapse.

    Filter rule: for all i in [0..4]: guess[i] != word[i]
    """
    candidates = [
        w
        for w in dictionary
        if w != guess and all(w[i] != guess[i] for i in range(WORD_LENGTH))
    ]

    if len(candidates) < 2:
        # Extremely unlikely; relax to any two different words
        candidates = [w for w in dictionary if w != guess]

    return tuple(random.sample(candidates, 2))  # type: ignore[return-value]


# ===================================================================
#  GAME STATE
# ===================================================================

class GameState:
    """
    Central state machine for a Quandle game.

    Lifecycle:
      1. Player submits Guess 1 -> entangled pair is generated.
      2. Superposition phase until a unique green triggers collapse.
      3. Collapsed phase until the active word is solved.
      4. Alternate reality phase until the other word is solved.
      5. Victory!
    """

    def __init__(self, dictionary: Set[str], dev_mode: bool = False):
        self.dictionary = dictionary
        self.dev_mode = dev_mode

        # Target words - set after Guess 1
        self.word_a: Optional[str] = None
        self.word_b: Optional[str] = None

        # Phase tracking
        self.phase = Phase.SUPERPOSITION
        self.active_target: Optional[str] = None
        self.collapsed_to: Optional[str] = None  # "A" or "B"

        # History & counters
        self.history: List[GuessRecord] = []
        self.guess_count: int = 0

        # Keyboard tracker: uppercase letter -> best known color
        self.keyboard: Dict[str, str] = {}

        # Per-turn event flags (reset each guess)
        self.collapse_just_happened: bool = False
        self.word_just_solved: Optional[str] = None
        self.game_over: bool = False
        self._first_guess: bool = True

    # -- public API -------------------------------------------------

    def process_guess(self, guess: str) -> GuessRecord:
        """
        Run a guess through the quantum evaluation pipeline.
        Returns the resulting GuessRecord for rendering.
        """
        self.guess_count += 1
        self.collapse_just_happened = False
        self.word_just_solved = None

        # On the very first guess, generate the entangled pair
        if self._first_guess:
            self.word_a, self.word_b = find_entangled_pair(
                guess, self.dictionary
            )
            self._first_guess = False

        # Route to the correct evaluation based on current phase
        if self.phase == Phase.SUPERPOSITION:
            record = self._eval_superposition(guess)
        else:
            record = self._eval_standard(guess)

        self.history.append(record)
        self._update_keyboard(record.tiles)
        return record

    # -- private helpers --------------------------------------------

    def _eval_superposition(self, guess: str) -> GuessRecord:
        """Evaluate under superposition rules and handle collapse."""
        tiles, collapse_target = evaluate_superposition(
            guess, self.word_a, self.word_b  # type: ignore[arg-type]
        )
        record = GuessRecord(
            guess, tiles, Phase.SUPERPOSITION, self.guess_count
        )

        if collapse_target:
            self.collapse_just_happened = True
            self.collapsed_to = collapse_target
            self.active_target = (
                self.word_a if collapse_target == "A" else self.word_b
            )
            self.phase = Phase.COLLAPSED
            record.note = "COLLAPSE"

            # Edge case: the collapse-causing guess also solves the word
            if guess == self.active_target:
                self._advance_after_solve(record, "COLLAPSE+SOLVE")

        return record

    def _eval_standard(self, guess: str) -> GuessRecord:
        """Evaluate under standard Wordle rules (Phase 2 or 3)."""
        tiles = evaluate_standard(guess, self.active_target)  # type: ignore[arg-type]
        record = GuessRecord(
            guess, tiles, self.phase, self.guess_count
        )

        if guess == self.active_target:
            if self.phase == Phase.COLLAPSED:
                self._advance_after_solve(record, "SOLVED")
            else:
                # Phase.ALTERNATE - both words solved -> victory!
                self.word_just_solved = self.active_target
                self.game_over = True
                record.note = "VICTORY"

        return record

    def _advance_after_solve(self, record: GuessRecord, note: str):
        """Transition from solved word to alternate reality."""
        self.word_just_solved = self.active_target
        other = (
            self.word_b if self.collapsed_to == "A" else self.word_a
        )
        self.active_target = other
        self.phase = Phase.ALTERNATE
        record.note = note

    def _update_keyboard(self, tiles: List[TileResult]):
        """Track the best-known state for each letter on the keyboard."""
        priority = {"green": 4, "yellow": 3, "purple": 2, "gray": 1}
        for tile in tiles:
            key = tile.letter.upper()
            cur = priority.get(self.keyboard.get(key, ""), 0)
            new = priority.get(tile.color, 0)
            if new > cur:
                self.keyboard[key] = tile.color


# ===================================================================
#  RENDERING - Rich Console UI
# ===================================================================

def render_banner(con: Console):
    """Print the colourful game title banner."""
    title = Text()
    colors = [
        "bright_green", "bright_yellow", "bright_magenta",
        "bright_cyan", "bright_green", "bright_yellow", "bright_magenta",
    ]
    title.append(f"{SYM_ATOM}  ", style="bright_cyan")
    for ch, col in zip("QUANDLE", colors):
        title.append(ch, style=f"bold {col}")
    title.append(f"  {SYM_ATOM}", style="bright_cyan")

    subtitle = Text("Quantum Word Deduction", style="dim italic")

    panel_content = Text.assemble(title, "\n", subtitle)
    con.print(
        Panel(
            Align.center(panel_content),
            border_style="bright_cyan",
            box=box.DOUBLE,
            padding=(1, 4),
        )
    )


def render_legend(con: Console):
    """Show the tile colour legend."""
    legend = Text("  ")
    legend.append(" G ", style=TILE_STYLES["green"])
    legend.append(" Correct pos  ", style="dim")
    legend.append(" Y ", style=TILE_STYLES["yellow"])
    legend.append(" Both words  ", style="dim")
    legend.append(" P ", style=TILE_STYLES["purple"])
    legend.append(" One word  ", style="dim")
    legend.append(" X ", style=TILE_STYLES["gray"])
    legend.append(" Neither", style="dim")
    con.print(legend)
    con.print()


def render_dev_info(con: Console, state: GameState):
    """Show target words when dev mode is active."""
    if not state.dev_mode:
        return
    dev = Text()
    dev.append(f"  {SYM_WRENCH} DEV ", style="bold black on bright_yellow")
    dev.append("  A: ", style="dim")
    dev.append(
        (state.word_a or "???").upper(), style="bold bright_green"
    )
    dev.append("  |  B: ", style="dim")
    dev.append(
        (state.word_b or "???").upper(), style="bold bright_magenta"
    )
    dev.append(f"  |  Phase: {state.phase.value}", style="dim")
    con.print(dev)
    con.print()


def render_phase_indicator(con: Console, state: GameState):
    """Display the current quantum phase and guess count."""
    phase_labels = {
        Phase.SUPERPOSITION: (f"{SYM_ATOM} SUPERPOSITION", "bright_cyan"),
        Phase.COLLAPSED:     (f"{SYM_BANG} COLLAPSED", "bright_red"),
        Phase.ALTERNATE:     (f"{SYM_SPIRAL} ALTERNATE REALITY", "bright_magenta"),
    }
    label, color = phase_labels[state.phase]

    line1 = Text()
    line1.append("  Phase: ", style="dim")
    line1.append(label, style=f"bold {color}")
    line1.append("    Guesses: ", style="dim")
    line1.append(str(state.guess_count), style="bold white")
    con.print(line1)

    # Target status line
    target = Text("  Target: ", style="dim")
    if state.phase == Phase.SUPERPOSITION:
        target.append("|psi>", style="bold bright_cyan")
        target.append(" = ", style="dim")
        target.append("[? ? ? ? ?]", style="bold bright_cyan")
        target.append(" + ", style="dim")
        target.append("[? ? ? ? ?]", style="bold bright_cyan")
    elif state.phase == Phase.COLLAPSED:
        target.append("[solving...]", style="bold bright_red")
        target.append("  (+)  ", style="dim")
        target.append("[locked]", style="dim strike")
    else:
        solved_word = (
            state.word_a
            if state.collapsed_to == "A"
            else state.word_b
        )
        target.append(
            f"[{solved_word.upper()}]",  # type: ignore[union-attr]
            style="bold green",
        )
        target.append("  (+)  ", style="dim")
        target.append("[solving...]", style="bold bright_magenta")
    con.print(target)
    con.print()


def _render_tile_row(tiles: List[TileResult]) -> Text:
    """Build a styled Text for one row of coloured tiles."""
    row = Text()
    for i, tile in enumerate(tiles):
        row.append(f" {tile.letter.upper()} ", style=TILE_STYLES[tile.color])
        if i < len(tiles) - 1:
            row.append(" ")
    return row


def render_board(con: Console, state: GameState):
    """
    Render the full board history.

    All previous guesses are displayed with their ORIGINAL phase
    colours - they never change when the game advances to a new phase.
    Phase-transition separators are inserted between blocks.
    """
    if not state.history:
        con.print(
            "  [dim]No guesses yet. Enter a 5-letter isogram to begin.[/]"
        )
        return

    phase_icon = {
        Phase.SUPERPOSITION: SYM_ATOM,
        Phase.COLLAPSED: SYM_BANG,
        Phase.ALTERNATE: SYM_SPIRAL,
    }

    prev_phase: Optional[Phase] = None

    for rec in state.history:
        # --- Phase-transition separator ---
        if prev_phase is not None and rec.phase != prev_phase:
            if rec.phase == Phase.COLLAPSED:
                con.print()
                con.print(
                    Rule(
                        f"{SYM_WARN} WAVE FUNCTION COLLAPSED TO ONE REALITY {SYM_WARN}",
                        style="bold bright_red",
                    )
                )
                con.print()
            elif rec.phase == Phase.ALTERNATE:
                con.print()
                con.print(
                    Rule(
                        f"{SYM_SPIRAL} ENTERING ALTERNATE REALITY {SYM_SPIRAL}",
                        style="bold bright_magenta",
                    )
                )
                con.print()

        # --- Tile row ---
        row = Text("  ")
        row.append_text(_render_tile_row(rec.tiles))
        row.append(
            f"   #{rec.guess_number} {phase_icon.get(rec.phase, '')}",
            style="dim",
        )

        # --- Annotations ---
        if rec.note == "COLLAPSE":
            row.append(f"  <- COLLAPSE!", style="bold bright_red")
        elif rec.note == "COLLAPSE+SOLVE":
            row.append(
                f"  <- COLLAPSE + SOLVED!", style="bold bright_green"
            )
        elif rec.note == "SOLVED":
            row.append(f"  <- SOLVED! {SYM_CHECK}", style="bold bright_green")
        elif rec.note == "VICTORY":
            row.append(f"  <- VICTORY! {SYM_STAR}", style="bold bright_green")

        con.print(row)
        prev_phase = rec.phase

    con.print()


def render_keyboard(con: Console, state: GameState):
    """Print a QWERTY keyboard colour-coded by known letter states."""
    rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    indents = ["  ", "   ", "    "]

    for indent, row_letters in zip(indents, rows):
        row_text = Text(indent)
        for ch in row_letters:
            color_key = state.keyboard.get(ch, None)
            style = KEY_STYLES.get(color_key, KEY_STYLES["unknown"])  # type: ignore[arg-type]
            row_text.append(f" {ch} ", style=style)
        con.print(row_text)
    con.print()


def render_collapse_event(con: Console, state: GameState):
    """Show a dramatic collapse notification panel."""
    if not state.collapse_just_happened:
        return
    # Don't show if the collapse also solved the word (combined message)
    if state.word_just_solved:
        return
    con.print()
    con.print(
        Panel(
            Align.center(
                Text.assemble(
                    Text(
                        f"{SYM_WARN}  WAVE FUNCTION COLLAPSED  {SYM_WARN}\n\n",
                        style="bold bright_red",
                    ),
                    Text(
                        "The quantum superposition has been observed!\n",
                        style="bright_yellow",
                    ),
                    Text(
                        "Reality has collapsed to a single word.\n",
                        style="dim",
                    ),
                    Text(
                        "Solve it to unlock the alternate reality.",
                        style="dim italic",
                    ),
                )
            ),
            border_style="bright_red",
            box=box.HEAVY,
            padding=(1, 4),
        )
    )


def render_word_solved(con: Console, state: GameState):
    """Show a celebration panel when one word is solved."""
    if not state.word_just_solved or state.game_over:
        return

    # Determine the right message
    if state.collapse_just_happened:
        # Collapse + solve happened on same guess
        header_text = f"{SYM_SPARK} COLLAPSE + INSTANT SOLVE! {SYM_SPARK}"
        header_style = "bold bright_yellow"
    else:
        header_text = f"{SYM_STAR}  WORD SOLVED!  {SYM_STAR}"
        header_style = "bold bright_green"

    con.print()
    con.print(
        Panel(
            Align.center(
                Text.assemble(
                    Text(f"{header_text}\n\n", style=header_style),
                    Text("You cracked: ", style="white"),
                    Text(
                        f"{state.word_just_solved.upper()}\n\n",
                        style="bold bright_green",
                    ),
                    Text(
                        "Now entering the ALTERNATE REALITY...\n",
                        style="bright_magenta",
                    ),
                    Text(
                        "Solve the entangled partner word!",
                        style="dim italic",
                    ),
                )
            ),
            border_style="bright_green",
            box=box.HEAVY,
            padding=(1, 4),
        )
    )


def render_victory(con: Console, state: GameState):
    """Show the glorious victory screen."""
    con.print()
    con.print(
        Panel(
            Align.center(
                Text.assemble(
                    Text(
                        f"{SYM_STAR}  QUANTUM DECOHERENCE COMPLETE!  {SYM_STAR}\n\n",
                        style="bold bright_green",
                    ),
                    Text("Word A:  ", style="dim"),
                    Text(
                        f"{state.word_a.upper()}\n",  # type: ignore[union-attr]
                        style="bold bright_green",
                    ),
                    Text("Word B:  ", style="dim"),
                    Text(
                        f"{state.word_b.upper()}\n\n",  # type: ignore[union-attr]
                        style="bold bright_magenta",
                    ),
                    Text("Solved in ", style="white"),
                    Text(
                        str(state.guess_count), style="bold bright_yellow"
                    ),
                    Text(" guesses\n\n", style="white"),
                    Text(
                        "Both realities have been observed.",
                        style="dim italic",
                    ),
                )
            ),
            border_style="bright_green",
            box=box.DOUBLE,
            padding=(1, 6),
        )
    )


def render_help(con: Console):
    """Print in-game help text."""
    con.print()
    con.print(
        Panel(
            Text.assemble(
                Text("HOW TO PLAY\n\n", style="bold bright_cyan"),
                Text(
                    "The target is a superposition of TWO 5-letter words.\n",
                    style="white",
                ),
                Text(
                    "Deduce both words using the coloured tile clues:\n\n",
                    style="dim",
                ),
                Text(" G ", style=TILE_STYLES["green"]),
                Text(
                    "  GREEN  -- Letter is in the correct position.\n"
                    "           Shared: correct for both words (no collapse).\n"
                    "           Unique: correct for one word only -> COLLAPSE!\n\n",
                    style="dim",
                ),
                Text(" Y ", style=TILE_STYLES["yellow"]),
                Text(
                    "  YELLOW -- Letter exists in BOTH words, wrong spot.\n\n",
                    style="dim",
                ),
                Text(" P ", style=TILE_STYLES["purple"]),
                Text(
                    "  PURPLE -- Letter exists in ONLY ONE word, wrong spot.\n"
                    "           This is your key clue for splitting the pair!\n\n",
                    style="dim",
                ),
                Text(" X ", style=TILE_STYLES["gray"]),
                Text(
                    "  GRAY   -- Letter is not in either word.\n\n",
                    style="dim",
                ),
                Text("COMMANDS\n", style="bold bright_yellow"),
                Text("  /dev   ", style="bold"),
                Text("Toggle dev mode (shows target words)\n", style="dim"),
                Text("  /board ", style="bold"),
                Text("Redraw the full board\n", style="dim"),
                Text("  /help  ", style="bold"),
                Text("Show this help\n", style="dim"),
                Text("  /quit  ", style="bold"),
                Text("Exit the game\n", style="dim"),
            ),
            border_style="bright_cyan",
            box=box.ROUNDED,
            title="[bold bright_cyan] Quandle Help [/]",
            padding=(1, 3),
        )
    )
    con.print()


# ===================================================================
#  MAIN GAME LOOP
# ===================================================================

def _full_redraw(con: Console, state: GameState):
    """Clear screen and redraw all persistent UI elements."""
    con.clear()
    render_banner(con)
    con.print()
    render_dev_info(con, state)
    render_phase_indicator(con, state)
    render_board(con, state)


def main():
    """Entry point for Quandle."""
    parser = argparse.ArgumentParser(
        description="Quandle -- A Quantum Wordle Variant"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable dev mode (shows target words)",
    )
    args = parser.parse_args()

    # Force rich to use the terminal (not legacy Windows renderer)
    con = Console(force_terminal=True)
    con.clear()
    render_banner(con)
    con.print()

    # Load dictionary
    con.print("  [dim]Initializing quantum dictionary...[/]")
    dictionary = load_dictionary(con)
    con.print()

    if len(dictionary) < 20:
        con.print("[bold red]  Error: dictionary too small to play![/]")
        sys.exit(1)

    # Initialise game state
    state = GameState(dictionary, dev_mode=args.dev)

    # Welcome screen
    render_legend(con)
    con.print(
        "  [dim]Type [bold]/help[/bold] for rules  |  "
        "[bold]/dev[/bold] toggle dev mode  |  "
        "[bold]/quit[/bold] to exit[/]"
    )
    con.print()

    # =========== GAME LOOP ===========
    while not state.game_over:
        # Prompt
        try:
            raw = con.input(
                f"[bold bright_cyan]  {SYM_ATOM} Enter guess > [/]"
            )
        except (EOFError, KeyboardInterrupt):
            con.print(
                "\n  [dim]Quantum observation cancelled. Goodbye![/]"
            )
            sys.exit(0)

        guess = raw.strip().lower()

        # -- Slash commands -----------------------------------------
        if guess == "/dev":
            state.dev_mode = not state.dev_mode
            tag = f"ON {SYM_WRENCH}" if state.dev_mode else "OFF"
            con.print(f"  [bold yellow]Dev mode: {tag}[/]\n")
            continue

        if guess in ("/quit", "/exit", "/q"):
            con.print(
                "  [dim]Exiting Quandle. "
                "See you in another timeline![/]"
            )
            sys.exit(0)

        if guess == "/help":
            render_help(con)
            continue

        if guess == "/board":
            _full_redraw(con, state)
            render_keyboard(con, state)
            continue

        # -- Input validation ---------------------------------------
        if len(guess) != WORD_LENGTH:
            con.print(
                f"  [bold red]! Must be exactly "
                f"{WORD_LENGTH} letters.[/]\n"
            )
            continue

        if not guess.isalpha():
            con.print("  [bold red]! Letters only, please.[/]\n")
            continue

        if guess not in dictionary:
            con.print(
                f"  [bold red]! '{guess.upper()}' is not "
                f"in the dictionary.[/]\n"
            )
            continue

        # -- Process the guess --------------------------------------
        state.process_guess(guess)

        # -- Full-screen redraw -------------------------------------
        _full_redraw(con, state)

        # Event notifications (below the board)
        render_collapse_event(con, state)
        render_word_solved(con, state)

        # Keyboard
        render_keyboard(con, state)

    # =========== VICTORY ===========
    render_victory(con, state)


if __name__ == "__main__":
    main()
