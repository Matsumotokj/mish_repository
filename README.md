# 書記マスター（Shoki Master）

> 秘匿性が高く自動文字起こしツールを持ち込めない業務（取り調べ・機密会議など）を想定し、
> **「聞いて・書き取る／要約する」スキルを鍛えるトレーニングアプリ**です。
> 生成AI（Gemini）が実践的な音声シナリオを動的に生成し、ユーザーの文字起こし・要約をAIが採点します。

ハッカソンのチーム開発作品（2025年10月・約1週間）。
本リポジトリは、就職活動のポートフォリオとして整備したものです。

**AWS 版**: このアプリを、AWS のサーバーレス構成（Bedrock・Polly・Lambda・DynamoDB・CloudFront）で一人で作り直しました → [Matsumotokj/shoki-master](https://github.com/Matsumotokj/shoki-master)

---

## 🎯 解決したい課題

取り調べや機密性の高い会議など、**録音や自動文字起こしツールの持ち込みが許されない現場**では、
担当者が「耳で聞いて、その場で正確に書き取る／要約する」能力が依然として求められます。

しかし、その練習をするには「リアルな音声題材」と「客観的な採点」が必要で、個人で用意するのは困難です。
書記マスターは、

1. **題材の自動生成** … Gemini が会社説明会・商品紹介などリアルな話し言葉のスクリプトを動的生成
2. **音声化** … Google Cloud Text-to-Speech で読み上げ（再生速度調整つき）
3. **客観採点** … 文字起こしは編集距離、要約はAIが多軸で採点

という一連の練習サイクルを、一人で何度でも回せる環境を提供します。

---

## ✨ 主な機能

| 機能 | 内容 |
|------|------|
| 題材の動的生成 | テーマ・文字数を指定すると Gemini が話し言葉のスクリプトを生成（JSON出力で安定化） |
| 音声合成・再生 | 句読点ごとに分割して Google TTS で音声化、Cloudinary 配信。再生速度・再生モードを選択可 |
| 文字起こしモード | 聞き取って入力 → **Damerau-Levenshtein 編集距離**で正答率を算出し、差分をハイライト表示 |
| 要約モード | 聞いた内容を要約 → **Gemini が忠実性・網羅性・明瞭さの3軸で採点**し、模範要約と根拠を提示 |

---

## 🛠 技術スタック

- **バックエンド**: Python 3 / Django 5.2
- **フロントエンド**: HTML / CSS / JavaScript（Django テンプレート）
- **生成AI**: Google Gemini API（`gemini-2.5-flash`）
- **音声合成**: Google Cloud Text-to-Speech
- **メディア配信**: Cloudinary（生成音声のホスティング）
- **デプロイ**: Render（Gunicorn / WhiteNoise）

### アーキテクチャ概要

```
[ユーザー] 
   │  テーマ・文字数を入力
   ▼
[apiapp]  AskGeminiView
   │  Gemini で話し言葉スクリプトを生成（JSON: {"text": ...}）
   ▼
[typeApp] PracticeView
   │  句読点で分割 → Google TTS で音声化 → Cloudinary へアップロード → 再生
   ▼
[ユーザー] 聞いて入力（文字起こし or 要約）
   ▼
[typeApp] ResultView
   ├─ 文字起こし → scoring_cmp.py（編集距離・差分ハイライト）
   └─ 要約      → apiapp.py get_gemini_scoring（Gemini JSON採点）
```

主要モジュール:

- [apiapp/apiapp.py](apiapp/apiapp.py) … Gemini 連携（題材生成・要約採点）
- [apiapp/scoring_cmp.py](apiapp/scoring_cmp.py) … 編集距離ベースの文字起こし採点・差分生成
- [apiapp/tts.py](apiapp/tts.py) … Google TTS 音声合成と Cloudinary アップロード
- [typeApp/views.py](typeApp/views.py) … 練習・採点画面のフロー制御

---

## 💡 工夫した点：LLM出力をJSONで安定させる堅牢なAPI連携

このアプリの肝は、**「揺らぎのある LLM の出力を、業務アプリで使える構造化データとして安定的に扱う」** 部分です。
LLM はそのまま使うと出力形式が一定せず、余計な前置きや ```（コードフェンス）を付けたり、稀に壊れた JSON を返したりします。
そこで [apiapp/apiapp.py](apiapp/apiapp.py) では、要約採点の API 連携を次のように堅牢化しました。

1. **JSON 強制 & 温度ゼロ** — `response_mime_type="application/json"` と `temperature=0` を指定し、出力を JSON・決定的に寄せる（`call_gemini_json`）。
2. **スキーマ検証** — 返ってきた JSON を `validate_schema` で検証。必須キーの有無・型・各小計の範囲（忠実性0〜50／網羅性0〜35／明瞭さ0〜15）まで確認し、不正なら例外を投げる。
3. **リトライ** — レート制限（429）を検知したら、エラーメッセージ中の待機秒数を読み取って一度だけ自動リトライ。
4. **後処理で点数を安定化** — `postprocess` で、要約が短すぎる／長すぎる場合の減点や、ハルシネーション検知時の調整を行い、最終スコアのブレを抑える。
5. **フォールバック** — どこかで失敗しても、画面が壊れないよう「スコア0＋理由」の整形済み JSON を必ず返す。

これにより、**「AI採点」という不確実性の高い機能を、ユーザーから見れば常に同じ形のレスポンスとして提供**できるようにしています。

採点の評価軸（システムプロンプトで定義）:

- 忠実性（50点）… 元文にない主張・数値・固有名詞を付け足していないか
- 網羅性（35点）… 元文の重要点をどれだけカバーできているか
- 明瞭・簡潔（15点）… 冗長・曖昧さが少なくまとまっているか

---

## 🚀 セットアップ

> ⚠️ **注意：本アプリの動作には外部APIキーの設定が必要です。**
> ポートフォリオ公開にあたり、開発時に使用していた **Gemini / Google Cloud / Cloudinary の各キーはすべて失効済み**です。
> そのため、このリポジトリをクローンしても**そのままでは動作しません**（ライブデモは提供していません）。
> 実装内容はソースコードでご確認ください。動かす場合は、ご自身のAPIキーを下記の環境変数に設定してください。

```bash
# 1. 取得
git clone https://github.com/<your-account>/<repo>.git
cd <repo>

# 2. 仮想環境と依存関係
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 環境変数（.env をプロジェクト直下に作成）
#    ※ .env は .gitignore 済み

# 4. 起動
python manage.py migrate
python manage.py runserver
```

### 必要な環境変数（`.env`）

| 変数 | 用途 |
|------|------|
| `SECRET_KEY` | Django のシークレットキー |
| `DEBUG` | 開発時 `True` / 本番 `False` |
| `GEMINI_API_KEY` | Gemini API（題材生成・要約採点） |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud TTS のサービスアカウントJSON（本番は文字列で指定） |
| `GOOGLE_APPLICATION_CREDENTIALS_PATH` | ↑のローカル用：JSONファイルへのパス |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | 生成音声のホスティング |
| `DATABASE_URL` | （任意）本番DB。未設定なら SQLite |

---

## 👥 チーム開発について / 担当範囲

本作品は**ハッカソンでのチーム開発**（2025年10月・約1週間）です。チームメンバーの貢献に敬意を表します。

筆者（リポジトリ所有者）の主な担当範囲:

- 要件定義
- フロントエンド全般
- バックエンド（Django）
- デプロイ・クラウド環境構築（Render / Cloudinary）

特に注力したのは、上記「**LLM出力をJSONで安定させる堅牢なAPI連携**」の設計・実装です。

---

## 🖼 スクリーンショット

> （ここに画面キャプチャ／デモGIFを追加予定）

---

## 📌 補足

- 開発期間：2025年10月（ハッカソン・約1週間）
- デプロイ先（当時）：Render（現在はAPIキー失効のため停止）
