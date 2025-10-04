import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

import io
# Google TTS (音声合成)
from google.cloud import texttospeech
import re

# # Audio Playback (再生)
# from pydub import AudioSegment
# import simpleaudio as sa

# Gemini (テキスト生成)
import google.generativeai as genai

# Google TTS (音声合成)
from google.cloud import texttospeech



# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを設定
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEYが.envファイルに設定されていません。")
genai.configure(api_key=api_key)

# --- 変更点：v1beta APIで利用可能なモデル名に修正 ---
# google-generativeaiライブラリはv1betaエンドポイントを呼び出すため、
# それに対応したプレビュー版のモデル名を指定する必要があります。
model = genai.GenerativeModel('gemini-2.5-flash')

# Google Cloud TTS API
# このスクリプトを実行する前に、認証キーのJSONファイルをダウンロードし、
# このスクリプトと同じフォルダに置いてください。
# google_api_key_path = "./service-account-key.json"
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_api_key_path
# ttl_client = texttospeech.TextToSpeechClient()



def get_gemini_response(content: str = "会社説明会で話されるような文章にしてください．"
                        , length_request: int = 300
                        , info: str = '') -> str:
    """
    指定された状況に基づき、文字起こし練習用のモノローグ形式の文章を生成します。
    出力は句点区切りで、改行を含まない単一のパラグラフになるように指示します。
    """

    length_min = length_request * 0.8
    length_max = length_request * 1.2
    
    prompt_for_script = f"""
##命令
日本語で任意の文章を条件に従ってできるだけ早く出力しなさい．

##条件
-{length_min}文字～{length_max}文字で出力すること．
-指定した文字数はpythonを用いて条件にあっているか確認すること．
-文章は1つ作成すること．
-出力は文字数の条件を満たした場合のみ出力すること．
-出力は作成した文章のみを出力すること．
-出力にアルファベットは含まないこと．
-内容は{content}
-出力のjsonのキーを**text**としてください．

# 形式の制約 (非常に重要)
- 話者名（例：「話者１：」）や括弧は含めないでください。

##備考
{info}
"""

    try:
        response = model.generate_content(prompt_for_script,generation_config={"response_mime_type": "application/json"})

        # # 返ってきたJSON文字列をPythonの辞書に変換
        data = json.loads(response.text)
        full_text = data["text"]

        print("response:", response)
        print("data:",data)
        print("full_text:",full_text)

        # 念のため、AIが誤って追加した可能性のある改行や不要な空白を削除する
        cleaned_text = full_text.replace("\n", "").strip()
        return cleaned_text
    except Exception as e:
        print(f"文章生成中にエラーが発生しました: {e}")
        return "エラーのため文章を生成できませんでした。"

# ====== 採点SYSTEM（厳しめ・平均≈80）とヘルパ ======
SYSTEM = """あなたは日本語の要約採点者です。評価は厳格に行います。
評価軸と配点（合計100点）:
- 忠実性(50): 元文にない主張・数値・固有名詞を付け足していないこと。1つでも明確な幻覚があれば0点。
- 網羅性(35): 元文の重要点のカバー率。主要論点の取りこぼしがあれば大きく減点。
- 明瞭・簡潔(15): 冗長表現や曖昧さが少なく、簡潔にまとまっているか。

採点分布の目安（重要）:
- 平均は80点前後。100点は稀。
- 多少うまく書けていても、忠実性か網羅性に欠ければ70点未満とする。

出力は必ず次のJSONのみ:
{
  "score_raw": 0..100 の整数,
  "subscores": { "faithfulness":0..50, "coverage":0..35, "clarity":0..15 },
  "hallucination": true/false,
  "notes": "80字以内の日本語の根拠",
  "best_summary": "120字以内の模範要約（忠実・網羅・簡潔を満たす）"
}
注意:
- best_summary は元文の事実に厳密に従うこと（捏造禁止）。
- 字数上限を超えないこと。
"""

def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n]

def _strip_fences(text: str) -> str:
    if not isinstance(text, str): return ""
    t = text.strip()
    t = re.sub(r"^```(\w+)?", "", t)
    t = re.sub(r"```$", "", t)
    return t.strip()

def _call_gemini_json(user_prompt: str):
    """JSONのみを返す呼び出し。429なら一度だけ待って再試行。"""
    def _once():
        return model.generate_content(
            [{"role": "user", "parts": [SYSTEM + "\n\n" + user_prompt]}],
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0,
            },
        )
    try:
        return _once()
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            m = re.search(r"retry in ([0-9.]+)s", msg.lower())
            wait = float(m.group(1)) if m else 3.0
            time.sleep(min(wait, 5.0))
            return _once()
        raise

def _validate_schema(d: dict):
    if not isinstance(d, dict):
        raise ValueError("not a JSON object")
    if "score_raw" not in d or "subscores" not in d or "hallucination" not in d:
        raise ValueError("required fields missing")
    raw = d["score_raw"]
    if not isinstance(raw, (int, float)):
        raise ValueError("score_raw must be number")
    ss = d["subscores"] or {}
    f = ss.get("faithfulness", 0)
    c = ss.get("coverage", 0)
    cl = ss.get("clarity", 0)
    if not (0 <= float(f) <= 50 and 0 <= float(c) <= 35 and 0 <= float(cl) <= 15):
        raise ValueError("subscores out of range")
    if not isinstance(d["hallucination"], (bool,)):
        raise ValueError("hallucination must be boolean")
    notes = d.get("notes", "")
    best_summary = d.get("best_summary", "")
    if isinstance(best_summary, str) and len(best_summary) > 160:
        best_summary = best_summary[:160]
    return int(raw), int(f), int(c), int(cl), bool(d["hallucination"]), str(notes or ""), str(best_summary or "")

def _gen_best_summary_from_source(source: str) -> str:
    """best_summary が欠けたら元文から生成（保険）。"""
    prompt = f"""次の文章を、事実に忠実に、120字以内で簡潔に要約してください。出力は本文のみ、引用符・箇条書き・コードフェンスなし。
# 文章
{source}
# 出力
本文のみ"""
    try:
        resp = model.generate_content(
            [{"role": "user", "parts": [prompt]}],
            generation_config={"response_mime_type": "text/plain", "temperature": 0},
        )
        txt = _strip_fences(resp.text).replace("\n", " ").strip()
        return txt[:120]
    except Exception:
        return ""

def _postprocess(raw: int, hallu: bool, length_ratio: float, notes: str, subscores: dict, best_summary: str):
    """
    目標: 平均80。基本 raw を尊重。
    - 幻覚あり: 上限 cap=70
    - 長さペナルティ: 短すぎ/長すぎのみ控えめ減点
    - 減点なし＆幻覚なし → final=raw
    - 理由に自動で減点理由を追記
    """
    penalty = 0
    reasons = []

    if length_ratio < 0.15:
        penalty -= 10; reasons.append("要約が短すぎ(-10)")
    elif length_ratio < 0.25:
        penalty -= 5;  reasons.append("要約がやや短い(-5)")
    if length_ratio > 0.80:
        penalty -= 10; reasons.append("要約が長すぎ(-10)")
    elif length_ratio > 0.60:
        penalty -= 5;  reasons.append("要約がやや長い(-5)")

    base = int(round(raw))
    cap  = 70 if hallu else 100

    if penalty == 0 and not hallu:
        final = base
    else:
        final = max(0, min(cap, base + penalty))

    shown = (notes or "").strip()
    if reasons:
        shown = f"{shown + ('／' if shown else '')}{'・'.join(reasons)}"

    return {
        "score": final,
        "score_raw": base,
        "penalty": int(penalty),
        "hallucination": hallu,
        "subscores": {
            "faithfulness": int(subscores.get("faithfulness", 0)),
            "coverage": int(subscores.get("coverage", 0)),
            "clarity": int(subscores.get("clarity", 0)),
        },
        "reasons": shown,
        "best_summary": best_summary or ""
    }

def get_gemini_scoring(correct_answer: str, user_input: str):
    """
    戻り値例:
    {
      "score": 82, "score_raw": 84, "penalty": -2, "hallucination": false,
      "subscores": {"faithfulness":45,"coverage":28,"clarity":11},
      "reasons": "〇〇が不足／要約がやや長い(-5)",
      "best_summary": "……（120字以内の模範要約）"
    }
    """
    source  = _truncate(correct_answer, 2000)
    summary = _truncate(user_input, 800)
    if not source or not summary:
        return {"score": 0, "score_raw": 0, "penalty": 0, "hallucination": False,
                "subscores": {"faithfulness":0,"coverage":0,"clarity":0},
                "reasons": "入力不足", "best_summary": ""}

    user_prompt = f"""# 元文
{source}

# 要約
{summary}

# 指示
SYSTEMの評価基準に厳格に従い、指定JSONのみで出力してください。
特に "best_summary" は120字以内で事実忠実・簡潔に。"""

    try:
        resp = _call_gemini_json(user_prompt)
        data = json.loads(resp.text)
        raw, f, c, cl, hallu, notes, best = _validate_schema(data)
        if not best:
            best = _gen_best_summary_from_source(source)
        length_ratio = len(summary) / max(1, len(source))
        return _postprocess(raw, hallu, length_ratio, notes,
                            {"faithfulness": f, "coverage": c, "clarity": cl},
                            best_summary=best)
    except Exception as e:
        return {"score": 0, "score_raw": 0, "penalty": 0, "hallucination": False,
                "subscores": {"faithfulness":0,"coverage":0,"clarity":0},
                "reasons": f"採点エラー: {e}", "best_summary": ""}
