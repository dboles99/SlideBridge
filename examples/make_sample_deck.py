"""Write a small synthetic deck to input/sample.pptx (run from the repository root)."""
from pathlib import Path

from tests.synthetic_decks import build_deck

Path("input").mkdir(exist_ok=True)
build_deck(Path("input/sample.pptx"), "A")
print("wrote input/sample.pptx")
