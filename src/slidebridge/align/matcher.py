"""Match an extracted PPT text row against a list of edited segments.

Strategy priority:
  1. Exact normalised match          → Unchanged
  2. Contained match (original ⊆ edited segment)  → Merged
  3. Fuzzy single-segment (score ≥ FUZZY_ACCEPT)   → Grammar / Clarity / Rewritten
  4. Adjacent-window merge (score ≥ WINDOW_ACCEPT) → Merged
  5. No match                        → Not Found
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from slidebridge.align.normalize import fingerprint, normalize_text
from slidebridge.align.segment import EditedSegment

# ── Thresholds ────────────────────────────────────────────────────────────────
FUZZY_ACCEPT  = 78    # minimum score for a single-segment fuzzy match
WINDOW_ACCEPT = 74    # minimum score for a multi-segment window match
SHORT_MIN_LEN = 8     # strings shorter than this skip pure fuzzy matching
MAX_WINDOW    = 3     # max segments to merge in a window


@dataclass
class MatchResult:
    matched_text: str
    score: float
    strategy: str       # exact | contained | fuzzy | window | none
    change_type: str    # Unchanged | Grammar | Clarity | Rewritten | Merged | Split | Not Found
    notes: str


def _classify(original: str, matched: str, score: float, strategy: str) -> str:
    """Derive a Change Type from match characteristics."""
    if not matched:
        return "Not Found"
    o = normalize_text(original)
    m = normalize_text(matched)
    if fingerprint(o) == fingerprint(m):
        return "Unchanged"
    if strategy in {"contained", "window"}:
        return "Merged"
    if len(m) > len(o) * 1.6:
        return "Merged"
    if len(m) < max(SHORT_MIN_LEN, len(o) * 0.55):
        return "Split"
    if score >= 92:
        return "Grammar"
    if score >= 80:
        return "Clarity"
    return "Rewritten"


def _best_fuzzy(fp_orig: str, segments: list[EditedSegment]) -> tuple[EditedSegment | None, float]:
    best: EditedSegment | None = None
    best_score = 0.0
    for seg in segments:
        s = max(
            fuzz.ratio(fp_orig, seg.fp),
            fuzz.partial_ratio(fp_orig, seg.fp),
            fuzz.token_sort_ratio(fp_orig, seg.fp),
        )
        if s > best_score:
            best_score = float(s)
            best = seg
    return best, best_score


def find_best_match(original_text: str, segments: list[EditedSegment]) -> MatchResult:
    """Return the best MatchResult for *original_text* against *segments*."""
    fp_orig = fingerprint(original_text)

    if not fp_orig:
        return MatchResult("", 0.0, "none", "Not Found", "Empty original row")

    # 1. Exact
    for seg in segments:
        if seg.fp == fp_orig:
            return MatchResult(seg.text, 100.0, "exact", "Unchanged", "Exact match")

    # 2. Contained (original fingerprint is a substring of a segment fingerprint)
    for seg in segments:
        if fp_orig and len(fp_orig) >= SHORT_MIN_LEN and fp_orig in seg.fp:
            ct = _classify(original_text, seg.text, 97.0, "contained")
            return MatchResult(
                seg.text, 97.0, "contained", ct,
                f"{ct} | original contained in edited segment",
            )

    # Skip unreliable fuzzy on very short strings
    if len(fp_orig) < SHORT_MIN_LEN:
        return MatchResult("", 0.0, "none", "Not Found",
                           "Too short for reliable fuzzy match")

    # 3. Fuzzy single-segment
    best_seg, best_score = _best_fuzzy(fp_orig, segments)
    if best_seg and best_score >= FUZZY_ACCEPT:
        ct = _classify(original_text, best_seg.text, best_score, "fuzzy")
        return MatchResult(
            best_seg.text, best_score, "fuzzy", ct,
            f"{ct} | fuzzy {best_score:.1f}",
        )

    # 4. Adjacent-window merge
    best_win_text = ""
    best_win_score = 0.0
    for i in range(len(segments)):
        for j in range(i, min(i + MAX_WINDOW, len(segments))):
            win = " ".join(s.text for s in segments[i : j + 1])
            win_fp = fingerprint(win)
            s = max(
                fuzz.partial_ratio(fp_orig, win_fp),
                fuzz.token_sort_ratio(fp_orig, win_fp),
            )
            if s > best_win_score:
                best_win_score = float(s)
                best_win_text = win

    if best_win_score >= WINDOW_ACCEPT:
        ct = _classify(original_text, best_win_text, best_win_score, "window")
        return MatchResult(
            best_win_text, best_win_score, "window", ct,
            f"{ct} | window merge {best_win_score:.1f}",
        )

    return MatchResult("", 0.0, "none", "Not Found", "No acceptable match found")
