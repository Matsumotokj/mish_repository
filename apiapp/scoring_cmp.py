# -*- coding: utf-8 -*-
"""
Minimal Typing Scoring Core (Python)
- ルール固定: 空白のみ無視 / 句読点は採点 / カタカナ⇔ひらがなは区別
- 方式: Damerau-OSA（挿入/削除/置換 + 隣接転置T=1）
- スコア: accuracy = (正規化後の出題長 - 編集距離) / 出題長 * 100
- 付属: 赤字ハイライト（HTML / ANSI）

使い方:/typeApp/viewsの時はこんな感じ？
    from scoring_core_min import grade, to_diff_html, to_diff_ansi

    r = grade(gold_text(正解文), typed_text（タイピング）)   # dict: accuracy(正答率), dist(ミス), len(元文の長さ), alignedA, alignedB(gold側とtyped側を1文字ずつ対応付けたリスト（足りない所は “∅”）), ops(ミスの種類)
    typed_html, gold_html = to_diff_html(r)   # Web表示
    typed_ansi, gold_ansi = to_diff_ansi(r)  # 端末表示用　　　　　（赤文字表示できる）
    context = {
                'mode': 'compare',
                'user_input': user_input,
                'correct_answer': correct_answer,
                'accuracy': r['accuracy'],     # 0-100
                'dist': r['dist'],             # 編集距離
                'length': r['len'],            # 正規化後goldの長さ
                'typed_html': typed_html,      # 差分（入力側）
                'gold_html': gold_html,        # 差分（正解側）
                'ops': r['ops'],               # ["M","S","I","D","T"...]
            }

        return render(request, "typeApp/result.html", context)
"""

from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Tuple

# --- 正規化（空白だけ無視） ---------------------------------------------------
_WS_RE = re.compile(r"\s+")

def normalize_ja(s: str) -> str:
    """空白のみ無視、NFKC正規化。句読点は残す／カナは区別。"""
    if not s:
        return ""
    t = unicodedata.normalize("NFKC", s)
    t = _WS_RE.sub("", t)
    return t

# --- Damerau-OSA: 距離 + 整列（M/S/I/D/T） -----------------------------------
def align_damerau(gold_raw: str, typed_raw: str) -> Dict:
    """
    戻り値:
      {
        "dist": int,
        "alignedA": List[str],  # gold 正規化後の整列結果
        "alignedB": List[str],  # typed 正規化後の整列結果
        "ops": List[str],       # "M","S","I","D","T"
        "normGold": str, "normTyped": str
      }
    """
    a = normalize_ja(gold_raw)
    b = normalize_ja(typed_raw)
    m, n = len(a), len(b)

    # DP と backtrack テーブル
    dp: List[List[int]] = [[0]*(n+1) for _ in range(m+1)]
    bt: List[List[str]] = [["E"]*(n+1) for _ in range(m+1)]
    for i in range(m+1):
        dp[i][0] = i
        bt[i][0] = "D"
    for j in range(n+1):
        dp[0][j] = j
        bt[0][j] = "I"
    bt[0][0] = "E"

    for i in range(1, m+1):
        ai = a[i-1]
        for j in range(1, n+1):
            bj = b[j-1]
            cost = 0 if ai == bj else 1
            best = dp[i-1][j-1] + cost
            op = "M" if cost == 0 else "S"
            # 削除
            cand = dp[i-1][j] + 1
            if cand < best:
                best, op = cand, "D"
            # 挿入
            cand = dp[i][j-1] + 1
            if cand < best:
                best, op = cand, "I"
            # 隣接転置
            if i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:
                cand = dp[i-2][j-2] + 1
                if cand < best:
                    best, op = cand, "T"
            dp[i][j] = best
            bt[i][j] = op

    # backtrace → 整列列
    i, j = m, n
    alignedA: List[str] = []
    alignedB: List[str] = []
    ops: List[str] = []
    while i > 0 or j > 0:
        op = bt[i][j]
        if op in ("M", "S"):
            alignedA.append(a[i-1]); alignedB.append(b[j-1]); ops.append(op)
            i -= 1; j -= 1
        elif op == "D":
            alignedA.append(a[i-1]); alignedB.append("∅"); ops.append("D")
            i -= 1
        elif op == "I":
            alignedA.append("∅"); alignedB.append(b[j-1]); ops.append("I")
            j -= 1
        elif op == "T":
            # 2文字を入れ替えとして展開（視覚化しやすいよう T を2個積む）
            alignedA.append(a[i-1]); alignedB.append(b[j-2]); ops.append("T")
            alignedA.append(a[i-2]); alignedB.append(b[j-1]); ops.append("T")
            i -= 2; j -= 2
        else:
            # フォールバック（理論上到達しない）
            if i > 0 and j > 0:
                alignedA.append(a[i-1]); alignedB.append(b[j-1]); ops.append("S")
                i -= 1; j -= 1
            elif i > 0:
                alignedA.append(a[i-1]); alignedB.append("∅"); ops.append("D")
                i -= 1
            else:
                alignedA.append("∅"); alignedB.append(b[j-1]); ops.append("I")
                j -= 1

    alignedA.reverse(); alignedB.reverse(); ops.reverse()
    return {"dist": dp[m][n], "alignedA": alignedA, "alignedB": alignedB,
            "ops": ops, "normGold": a, "normTyped": b}

# --- 採点（accuracy / dist / len） ------------------------------------------
def grade(gold_raw: str, typed_raw: str) -> Dict[str, object]:
    r = align_damerau(gold_raw, typed_raw)
    N = len(r["normGold"])
    dist = r["dist"]
    accuracy = (0 if typed_raw else 100) if N == 0 else round(((N - dist) / N) * 100)
    return {
        "accuracy": accuracy, "dist": dist, "len": N,
        "alignedA": r["alignedA"], "alignedB": r["alignedB"], "ops": r["ops"],
        "normGold": r["normGold"], "normTyped": r["normTyped"],
    }

# --- 可視化: HTML（赤字） ----------------------------------------------------
def _esc_html(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#039;"))

def to_diff_html(result: Dict[str, object]) -> Tuple[str, str]:
    """
    戻り値: (typed_html, gold_html)
      - typed側: S/I/T → 赤, D(欠落) → 赤□
      - gold側 : S/D/T → 赤, I(余分) → 赤□
    """
    typed_parts: List[str] = []
    gold_parts: List[str] = []
    A: List[str] = result["alignedA"]  # gold
    B: List[str] = result["alignedB"]  # typed
    ops: List[str] = result["ops"]

    for k, op in enumerate(ops):
        chT = B[k]; chG = A[k]
        # typed
        if op == "M":
            typed_parts.append(f'<span class="ok">{_esc_html(chT)}</span>')
        elif op == "D":
            typed_parts.append('<span class="err placeholder">□</span>')
        else:  # S / I / T
            typed_parts.append(f'<span class="err">{_esc_html(chT)}</span>')
        # gold
        if op == "M":
            gold_parts.append(f'<span class="ok">{_esc_html(chG)}</span>')
        elif op == "I":
            gold_parts.append('<span class="err placeholder">□</span>')
        else:  # S / D / T
            gold_parts.append(f'<span class="err">{_esc_html(chG)}</span>')

    return ("".join(typed_parts), "".join(gold_parts))

# --- 可視化: 端末 ANSI（赤） -------------------------------------------------
_RED = "\x1b[31m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"

def to_diff_ansi(result: Dict[str, object]) -> Tuple[str, str]:
    """
    戻り値: (typed_ansi, gold_ansi)
      - typed側: S/I/T → 赤, D(欠落) → 赤□
      - gold側 : S/D/T → 赤, I(余分) → 赤□
    """
    typed_parts: List[str] = []
    gold_parts: List[str] = []
    A: List[str] = result["alignedA"]
    B: List[str] = result["alignedB"]
    ops: List[str] = result["ops"]

    for k, op in enumerate(ops):
        chT = B[k]; chG = A[k]
        # typed
        if op == "M":
            typed_parts.append(chT)
        elif op == "D":
            typed_parts.append(f"{_RED}{_BOLD}□{_RESET}")
        else:
            typed_parts.append(f"{_RED}{_BOLD}{chT}{_RESET}")
        # gold
        if op == "M":
            gold_parts.append(chG)
        elif op == "I":
            gold_parts.append(f"{_RED}{_BOLD}□{_RESET}")
        else:
            gold_parts.append(f"{_RED}{_BOLD}{chG}{_RESET}")

    return ("".join(typed_parts), "".join(gold_parts))

__all__ = ["normalize_ja", "align_damerau", "grade", "to_diff_html", "to_diff_ansi"]


