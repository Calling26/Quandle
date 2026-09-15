# ⚛️ QUANDLE — A Quantum Wordle Variant

**Quandle** is a quantum-inspired word deduction game where the target word exists in a superposition of **two different words**. Every guess you make acts as an observation that collapses the wave function based on quantum tile rules!

Available in two formats:
1. **Interactive Web App** (`index.html`)
2. **Terminal CLI Application** (`quandle.py`)

---

## 🎮 How to Play

### 1. Superposition Phase
At the start, the secret word exists as **both Word A and Word B** simultaneously:
$$\left|\psi\right\rangle = \frac{1}{\sqrt{2}}\Big(\text{|Word A}\rangle + \text{|Word B}\rangle\Big)$$

Every 5-letter isogram guess is evaluated against both target words using special **Quantum Tile Rules**:

| Tile Color | Meaning | Wave Function Effect |
| :--- | :--- | :--- |
| 🟩 **Green** | Correct letter in the correct position for **both** words (Shared) | Superposition preserved |
| 🟩 **Green** | Correct letter in the correct position for **one** word (Unique) | 💥 **Triggers Collapse!** |
| 🟨 **Yellow** | Letter exists in **both** words, but wrong position | Superposition preserved |
| 🟪 **Purple** | Letter exists in **only one** word, wrong position | Superposition preserved |
| ⬛ **Gray** | Letter is in **neither** word | Superposition preserved |

> ⚠️ **The Paradox Rule:** If a single guess produces unique green tiles for *both* Word A and Word B at the same time, a quantum paradox occurs! The collapse is canceled, and those tiles turn **Purple**.

---

### 2. Collapsed Phase & Alternate Reality
- **Collapse:** Once a unique green tile appears, reality collapses to **one target word**.
- **Solving:** Solve the collapsed target word to finish Phase 2.
- **Alternate Reality:** Once the first word is solved, you enter an alternate timeline to solve the remaining word and achieve total victory! 🏆

---

## 🚀 Getting Started

### 🌐 Web Version
Simply open [`index.html`](index.html) in any modern web browser! 

*(Or try the live GitHub Pages link once deployed).*

---

### 🐍 Terminal CLI Version

#### Prerequisites
- Python 3.8+
- `rich` library for terminal formatting

#### Installation & Execution
```bash
pip install rich
python quandle.py
```

#### Developer Mode
To reveal the superposed target words during play:
```bash
python quandle.py --dev
```

---

## 📁 Repository Structure

```
Quandle/
├── index.html               # Web-based visual implementation
├── quandle.py               # Python terminal-based game
├── .quandle_wordcache.txt   # Cached 5-letter isogram dictionary
├── .gitignore
└── README.md
```

---

## 📄 License

MIT License — Feel free to fork, adapt, and experiment!
