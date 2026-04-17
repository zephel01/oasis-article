#!/usr/bin/env python3
"""
note_rewriter.py
────────────────────────────────────────────────────────────
Note記事のAI臭を除去してMarkdownに書き直すスクリプト (v4)。
スタイルテンプレートを読み込んで自分の文体に合わせてリライトできる。

v4 の改善点:
  - ローカルの .md / .txt ファイルを直接入力できるように
  - --deai オプション: AI臭チェック＆修正提案モード（LLMリライトなし）
  - ソース引数が URL でもファイルパスでも自動判定

v3 の改善点:
  - --format オプションで出力形式を選択可能 (md / txt / html)
  - 複数フォーマットの同時出力に対応 (--format md,txt,html)

v2 の改善点:
  - コードブロックをプレースホルダで保護し、LLMに一切触らせない
  - ストリーミング中の強力な反復検出・早期中断
  - リライト後に差分検証し、コードブロック改変があれば原文に差し戻し
  - プロンプトエコー（指示文のオウム返し）の徹底除去
  - セクション分割時のコードブロック境界保護

使い方:
  python note_rewriter.py https://note.com/user/n/nXXXXXXX
  python note_rewriter.py article_draft.md
  python note_rewriter.py article_draft.md --deai
  python note_rewriter.py https://note.com/user/n/nXXXXXXX --template style_template.md
  python note_rewriter.py https://note.com/user/n/nXXXXXXX --model qwen2.5:14b
  python note_rewriter.py https://note.com/user/n/nXXXXXXX --format txt
  python note_rewriter.py https://note.com/user/n/nXXXXXXX --format md,txt,html
  python note_rewriter.py https://note.com/user/n/nXXXXXXX --dry-run

オプション:
  --template    文体テンプレートのパス (なければデフォルトの指示を使用)
  --model       Ollamaモデル名 (デフォルト: 環境変数 NOTE_REWRITER_MODEL または LFM-2.5-JP)
  --output      出力先ファイルパス (拡張子は --format に合わせて自動付与)
  --format      出力形式: md, txt, html (カンマ区切りで複数指定可。デフォルト: md)
  --host        OllamaホストURL (デフォルト: http://localhost:11434)
  --dry-run     原文取得のみ、LLMは呼ばない
  --no-title    タイトルはリライトしない
  --chunk-size  1回のLLM呼び出しに渡す最大文字数
  --deai        AI臭チェック＆修正提案モード (LLMリライトなしでパターンマッチ検出)
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ═════════════════════════════════════════════
# ロガー設定
# ═════════════════════════════════════════════

def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """ログファイル付きのロガーを作成する"""
    logger = logging.getLogger("note_rewriter")
    logger.setLevel(logging.DEBUG)

    # ログディレクトリ作成
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # ファイル名: logs/20260304_153045.log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{timestamp}.log"

    # ファイルハンドラ（DEBUG以上すべて記録）
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # コンソールハンドラ（INFO以上のみ表示）
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"ログファイル: {log_file.resolve()}")
    return logger


# グローバルロガー（main() で初期化）
log: logging.Logger = logging.getLogger("note_rewriter")


# ═════════════════════════════════════════════
# 環境変数で上書きできる設定
# ═════════════════════════════════════════════

import os

DEFAULT_MODEL = os.environ.get("NOTE_REWRITER_MODEL", "schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest")
DEFAULT_HOST = os.environ.get("NOTE_REWRITER_HOST", "http://localhost:11434")
DEFAULT_LOG_DIR = os.environ.get("NOTE_REWRITER_LOG_DIR", "logs")
DEFAULT_FORMAT = os.environ.get("NOTE_REWRITER_FORMAT", "md")
DEFAULT_TEMPERATURE = float(os.environ.get("NOTE_REWRITER_TEMPERATURE", "0.2"))


# ═════════════════════════════════════════════
# 定数
# ═════════════════════════════════════════════

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ストリーミング中の反復検出に使うしきい値
MAX_IDENTICAL_LINES = 3       # 同一行がこれ以上連続したら中断
MAX_IDENTICAL_BLOCKS = 2      # 同一ブロック（複数行パターン）がこれ以上繰り返されたら中断
REPEAT_WINDOW_CHARS = 300     # 直近N文字でパターンマッチ

# プロンプトエコー検出パターン
PROMPT_ECHO_PATTERNS = [
    "次の本文を自然な日本語に書き直してください",
    "本文だけを返してください",
    "要約せず、内容を落とさないでください",
    "[本文開始]",
    "[本文終了]",
    "コマンド、コード、URL、モデル名、数値、見出しは変えない",
    "説明や前置きは不要",
    "要約は禁止",
    "行や箇条書き、見出しは維持",
    "スタイルガイドに従ってリライト",
    "Markdown形式で出力",
    "技術的な内容・コードは変えないこと",
    "元の情報を省略せず",
    "情報の欠落・追加はしない",
    "━━━━━",
]

DEFAULT_TEMPLATE_NAMES = ["style_template.md", "my_style.md", "template.md"]

DEFAULT_STYLE_INSTRUCTIONS = """
## 文体の方針
- 口語調・カジュアルなですます体
- 「〜してみた」「〜ハマった」「〜できた」「〜だった」を積極的に使う
- 一人称は省略か「自分」。「筆者」「私たち」は使わない
- 短い文を多用。一文は60字以内を目安に
- 結論を先に、詳細は後に
- 過剰な丁寧表現・持って回った言い回しは削除

## 除去するAI臭パターン（全AI共通）
- 「〜と言えるでしょう」→ 断定か感想に
- 「本記事では〜ご紹介」→ 削除か「ここでは〜」に
- 「まとめ」の教科書的な締め → 感想・次にやりたいことに
- 「はじめに」「概要」の冒頭 → いきなり本題から
- 「〜が求められます」→「〜が必要」に
- 「〜を実現しました」→「〜できた」に
- 「いかがでしたか？」→ 削除
- 「それでは〜見ていきましょう」→ 削除
- 「〜について解説します」→ 削除。いきなり書く
- 「〜することが可能です」→「〜できる」に
- 「〜を活用することで」→「〜を使えば」に
- 「〜は非常に重要です」→「〜が大事」に

## ChatGPT特有の癖
- 「素晴らしい質問ですね」的な前置き → 全削除
- 「以下にまとめました」「具体的には以下の通りです」→ 削除
- 「お役に立てれば幸いです」「参考になれば幸いです」→ 削除
- 「ステップバイステップで」→ 削除か「順番に」に
- 「〜に焦点を当てて」→「〜について」に

## Claude特有の癖
- 「〜ですね」「〜かもしれません」の多用 → 断定できるなら断定
- 「ただし」「一方で」の過剰な留保 → 本当に必要な場合だけ
- 「〜と考えられます」→ 断定か「〜だと思う」に

## Gemini特有の癖
- 「ポイントは3つあります」的なナンバリング予告 → 削除
- 太字の多用 → 本当に強調したい箇所だけ
- 聞かれてない補足情報 → 削除

## Grok特有の癖
- 「ぶっちゃけ」「まぁ」→ 削除か文体に合わせる
- 皮肉やブラックユーモア → 技術記事では削除
"""


# ═════════════════════════════════════════════
# Note記事の取得
# ═════════════════════════════════════════════

def extract_note_key(url: str) -> str:
    """URL から note キーを取り出す (例: n6b236da76680)"""
    m = re.search(r"/n/([a-z0-9]+)/?$", url)
    if not m:
        raise ValueError(f"Note URLとして認識できませんでした: {url}")
    return m.group(1)


def fetch_via_api(note_key: str) -> dict | None:
    """Note 非公式APIで記事を取得"""
    api_url = f"https://note.com/api/v3/notes/{note_key}"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            note = r.json().get("data", {})
            if note.get("body"):
                return note
    except Exception:
        pass
    return None


def fetch_via_html(url: str) -> dict | None:
    """ページHTMLの __NEXT_DATA__ から記事を取得"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script:
            data = json.loads(script.string)
            note = (
                data.get("props", {})
                    .get("pageProps", {})
                    .get("note")
            )
            if note and note.get("body"):
                return note

        # フォールバック: OGPメタから最低限取得
        title, description = "", ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title and not title:
            title = og_title.get("content", "")
        og_desc = soup.find("meta", {"property": "og:description"})
        if og_desc:
            description = og_desc.get("content", "")

        if title:
            return {"name": title, "body": description or "(本文を取得できませんでした)"}

    except Exception as e:
        print(f"[WARN] HTML取得エラー: {e}", file=sys.stderr)

    return None


def html_to_markdown(html_body: str) -> str:
    """記事HTMLをMarkdown的なプレーンテキストに変換"""
    soup = BeautifulSoup(html_body, "html.parser")

    protected: dict[str, str] = {}

    # コードブロックを保護 (pre / code)
    for i, tag in enumerate(soup.find_all(["pre", "code"])):
        placeholder = f"__PROTECTED_{i}__"
        protected[placeholder] = f"\n```\n{tag.get_text()}\n```\n"
        tag.replace_with(f"\n\n{placeholder}\n\n")

    # Note の構成図・画像ブロック (figure) を保護
    for i, tag in enumerate(soup.find_all("figure"), start=len(protected)):
        img = tag.find("img")
        if img:
            alt = img.get("alt", "")
            src = img.get("src", "")
            content = f"\n![{alt}]({src})\n"
        else:
            content = f"\n```\n{tag.get_text()}\n```\n"
        placeholder = f"__PROTECTED_{i}__"
        protected[placeholder] = content
        tag.replace_with(f"\n\n{placeholder}\n\n")

    # 見出しタグをMarkdown見出しに変換
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        level = int(tag.name[1])
        tag.replace_with(f"\n\n{'#' * level} {tag.get_text(strip=True)}\n\n")

    # リストタグ
    for tag in soup.find_all("li"):
        tag.replace_with(f"\n- {tag.get_text(strip=True)}")

    text = soup.get_text(separator="\n")

    # 保護ブロックを戻す
    for placeholder, content in protected.items():
        text = text.replace(placeholder, content)

    # 連続改行を整理
    text = re.sub(r"\n{3,}", "\n\n", text)

    # コードブロック外にある矢印・図的なテキスト行を保護
    text = _protect_inline_diagrams(text)

    return text.strip()


def _protect_inline_diagrams(text: str) -> str:
    """コードブロック外の構成図っぽい行をコードブロックで囲む"""
    lines = text.split("\n")
    result = []
    diagram_buf = []
    in_code = False

    BOX_CHARS = re.compile(r"[─│┌┐└┘├┤┬┴┼━┃╔╗╚╝╠╣╦╩╬▼▲◀▶]")
    PIPELINE_LINE = re.compile(r"^\s*\[\d+/\d+\].*[→←]")

    def is_diagram_line(line: str) -> bool:
        if line.startswith("#"):
            return False
        if BOX_CHARS.search(line):
            return True
        if PIPELINE_LINE.match(line):
            return True
        return False

    def flush_diagram():
        if diagram_buf:
            result.append("```")
            result.extend(diagram_buf)
            result.append("```")
            diagram_buf.clear()

    for line in lines:
        if line.strip().startswith("```"):
            flush_diagram()
            in_code = not in_code
            result.append(line)
            continue

        if in_code:
            result.append(line)
            continue

        if is_diagram_line(line):
            diagram_buf.append(line)
        else:
            flush_diagram()
            result.append(line)

    flush_diagram()
    return "\n".join(result)


def fetch_article(url: str) -> dict:
    """記事を取得して {'title', 'body_text', 'url'} を返す"""
    note_key = extract_note_key(url)
    print(f"[1/3] 記事を取得中... (key: {note_key})")

    note = fetch_via_api(note_key)
    if not note:
        print("       → API取得失敗。HTMLから取得を試みます...")
        note = fetch_via_html(url)

    if not note:
        raise RuntimeError(
            "記事の取得に失敗しました。\n"
            "  - URLが正しいか確認してください\n"
            "  - 有料記事・ログイン必要な記事は取得できません"
        )

    title = note.get("name", "untitled")
    body_raw = note.get("body", "")

    body_text = html_to_markdown(body_raw) if body_raw.strip().startswith("<") else body_raw.strip()

    print(f"       → 取得成功: 「{title}」({len(body_text)}文字)")
    return {"title": title, "body_text": body_text, "url": url}


# ═════════════════════════════════════════════
# ローカルファイル読み込み
# ═════════════════════════════════════════════

def is_url(source: str) -> bool:
    """ソース文字列がURLかファイルパスかを判定する"""
    return source.startswith("http://") or source.startswith("https://")


def load_local_file(filepath: str) -> dict:
    """ローカルの .md / .txt ファイルを読み込んで記事dictを返す"""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {filepath}")

    if p.suffix.lower() not in (".md", ".txt", ".markdown"):
        raise ValueError(
            f"未対応のファイル形式です: {p.suffix}\n"
            "  対応形式: .md, .txt, .markdown"
        )

    text = p.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"ファイルが空です: {filepath}")

    # タイトル抽出: 最初の # 見出し or ファイル名
    title = p.stem
    lines = text.strip().split("\n")
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    print(f"[1/3] ローカルファイルを読み込み中... ({p.name})")
    print(f"       → 読み込み成功: 「{title}」({len(text)}文字)")

    return {"title": title, "body_text": text, "url": f"file://{p.resolve()}"}


# ═════════════════════════════════════════════
# コードブロック保護
# ═════════════════════════════════════════════

class CodeBlockProtector:
    """
    コードブロックと画像をプレースホルダに置換してLLMに渡さないようにする。
    リライト後にプレースホルダを元のブロックに差し戻す。
    """

    PLACEHOLDER_PREFIX = "【CODE_BLOCK_"
    PLACEHOLDER_SUFFIX = "】"

    def __init__(self):
        self._blocks: dict[str, str] = {}
        self._counter = 0

    def protect(self, text: str) -> str:
        """テキスト中のコードブロックと画像を保護する"""

        def replace_code_block(m: re.Match) -> str:
            key = self._make_key()
            self._blocks[key] = m.group(0)
            return f"\n{key}\n"

        # コードブロック（```...```）を保護
        text = re.compile(
            r"^```[^\n]*\n.*?^```",
            re.MULTILINE | re.DOTALL,
        ).sub(replace_code_block, text)

        # 画像 (![alt](url)) を保護
        def replace_image(m: re.Match) -> str:
            key = self._make_key()
            self._blocks[key] = m.group(0)
            return key

        text = re.compile(r"!\[[^\]]*\]\([^)]+\)").sub(replace_image, text)

        return text

    def restore(self, text: str) -> str:
        """プレースホルダを元のブロックに戻す"""
        for key, block in self._blocks.items():
            text = text.replace(key, block)
        return text

    @property
    def blocks(self) -> dict[str, str]:
        return dict(self._blocks)

    def _make_key(self) -> str:
        self._counter += 1
        return f"{self.PLACEHOLDER_PREFIX}{self._counter}{self.PLACEHOLDER_SUFFIX}"


# ═════════════════════════════════════════════
# テンプレート読み込み
# ═════════════════════════════════════════════

def load_template(template_path: str | None, script_dir: Path) -> str:
    """テンプレートファイルを読み込む。見つからない場合はデフォルトを返す"""
    if template_path:
        p = Path(template_path)
        if not p.exists():
            print(f"[WARN] テンプレートファイルが見つかりません: {template_path}", file=sys.stderr)
            return DEFAULT_STYLE_INSTRUCTIONS
        content = p.read_text(encoding="utf-8")
        print(f"       → テンプレート読み込み: {p.name}")
        return content

    for name in DEFAULT_TEMPLATE_NAMES:
        p = script_dir / name
        if p.exists():
            content = p.read_text(encoding="utf-8")
            print(f"       → テンプレート自動検出: {p.name}")
            return content

    print("       → テンプレートなし。デフォルトの指示を使用")
    return DEFAULT_STYLE_INSTRUCTIONS


def build_system_prompt(style_guide: str) -> str:
    """スタイルガイドからシステムプロンプトを構築"""
    return f"""あなたは日本語技術ブログのリライターです。
以下のスタイルガイドに従って文章を書き直してください。

{style_guide}

【必ず守ること】
- 技術的な内容（コマンド、設定値、モデル名、バージョン等）は絶対に変えない
- 【CODE_BLOCK_N】のようなプレースホルダはそのまま一字一句変えずに残す
- 見出しの構造（##, ###）は維持する
- 情報の欠落・追加はしない。あくまで日本語テキスト部分のリライトのみ
- 出力はMarkdown形式で本文のみ。前置きや説明は一切不要
"""


# ═════════════════════════════════════════════
# モデル特性
# ═════════════════════════════════════════════

def get_model_size_b(model: str) -> float | None:
    """モデル名から推定パラメータ数(B)を返す"""
    m = re.search(r"(\d+\.?\d*)b", model.lower())
    if not m:
        return None
    return float(m.group(1))


def is_small_model(model: str) -> bool:
    """3B以下のモデルかを判定"""
    size_b = get_model_size_b(model)
    return size_b is not None and size_b <= 3.0


def guess_chunk_size(model: str) -> int:
    """モデルサイズから適切なチャンクサイズを推定"""
    params = get_model_size_b(model)
    if params is not None:
        if params <= 2:
            return 500
        elif params <= 4:
            return 900
        elif params <= 8:
            return 1600
        elif params <= 15:
            return 2200
        else:
            return 2800
    return 2000


# ═════════════════════════════════════════════
# Ollama 呼び出し（強力な反復検出つき）
# ═════════════════════════════════════════════

class RepetitionDetector:
    """ストリーミング中の反復パターンを検出する"""

    def __init__(self):
        self._lines: list[str] = []          # 正規化済みの行バッファ
        self._raw_buffer: str = ""            # 生テキストバッファ
        self._line_counts: dict[str, int] = {}  # 行ごとの出現回数
        self._aborted = False
        self._reason = ""

    def feed(self, chunk: str) -> bool:
        """テキストチャンクを食べて、中断すべきならTrueを返す"""
        if self._aborted:
            return True

        self._raw_buffer += chunk

        # 行単位の反復検出
        for line in chunk.splitlines():
            normalized = self._normalize(line)
            if not normalized:
                continue

            self._lines.append(normalized)
            self._line_counts[normalized] = self._line_counts.get(normalized, 0) + 1

            # 同一行の連続をチェック
            if len(self._lines) >= MAX_IDENTICAL_LINES:
                recent = self._lines[-MAX_IDENTICAL_LINES:]
                if len(set(recent)) == 1:
                    self._abort(f"同一行の連続反復を検出: '{normalized[:40]}...'")
                    return True

        # ブロック単位の反復検出（直近の文字列でパターン探索）
        tail = self._raw_buffer[-REPEAT_WINDOW_CHARS * 2:]
        if len(tail) > 100:
            if self._detect_block_repeat(tail):
                return True

        # 空コードフェンスの連打検出
        fence_count = self._raw_buffer[-500:].count("```")
        content_between_fences = re.sub(r"```[^\n]*", "", self._raw_buffer[-500:]).strip()
        if fence_count >= 8 and len(content_between_fences) < fence_count * 5:
            self._abort("空のコードフェンス反復を検出")
            return True

        # 単一行の過剰反復（全体で同じ行が多すぎる）
        for line_text, count in self._line_counts.items():
            if count >= 8 and line_text not in ("```", "---", ""):
                self._abort(f"行の過剰反復を検出 (x{count}): '{line_text[:40]}...'")
                return True

        return False

    def _detect_block_repeat(self, text: str) -> bool:
        """複数行からなるブロックの反復を検出"""
        # テキストを後ろ半分と前半分に分けて一致を見る
        half = len(text) // 2
        if half < 30:
            return False

        # スライディングウィンドウで反復パターンを探す
        for pattern_len in range(30, min(half, 200), 10):
            pattern = text[-pattern_len:]
            # このパターンが直前に何回出現するか
            search_area = text[:-pattern_len]
            count = 0
            pos = 0
            while True:
                idx = search_area.find(pattern, pos)
                if idx == -1:
                    break
                count += 1
                pos = idx + 1

            if count >= MAX_IDENTICAL_BLOCKS:
                self._abort(f"ブロック反復パターンを検出 (x{count + 1}, {pattern_len}文字)")
                return True

        return False

    def _normalize(self, line: str) -> str:
        return re.sub(r"\s+", " ", line.strip())

    def _abort(self, reason: str):
        self._aborted = True
        self._reason = reason

    @property
    def aborted(self) -> bool:
        return self._aborted

    @property
    def reason(self) -> str:
        return self._reason


def call_ollama(
    prompt: str,
    system: str,
    model: str,
    host: str,
    temperature: float = DEFAULT_TEMPERATURE,
    timeout: int = 600,
) -> str:
    """Ollama の /api/chat を呼んでレスポンスを返す（反復検出・ログ・タイムアウト付き）"""
    api_url = f"{host.rstrip('/')}/api/chat"

    options: dict = {
        "temperature": temperature,
        "top_p": 0.9,
        "repeat_penalty": 1.15,
    }

    if is_small_model(model):
        options.update({
            "temperature": 0.1,
            "num_ctx": 2048,
            "repeat_penalty": 1.2,
            "num_predict": 1200,
        })
    else:
        size = get_model_size_b(model)
        if size and size <= 8:
            options["num_predict"] = 2000
        else:
            options["num_predict"] = 3000

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "options": options,
    }

    log.debug(f"=== Ollama API呼び出し ===")
    log.debug(f"  model: {model}")
    log.debug(f"  options: {json.dumps(options, ensure_ascii=False)}")
    log.debug(f"  system prompt ({len(system)}文字): {system[:200]}...")
    log.debug(f"  user prompt ({len(prompt)}文字): {prompt[:300]}...")

    result = []
    detector = RepetitionDetector()
    t_start = time.time()
    first_token_time = None
    token_count = 0
    last_activity = time.time()
    STALL_TIMEOUT = 120  # 120秒トークンが来なければ中断

    try:
        with requests.post(api_url, json=payload, stream=True, timeout=(30, timeout)) as r:
            r.raise_for_status()
            log.debug(f"  HTTP接続OK (status: {r.status_code})")

            for line in r.iter_lines():
                if not line:
                    # ストール検出
                    if time.time() - last_activity > STALL_TIMEOUT:
                        log.warning(f"  ストール検出: {STALL_TIMEOUT}秒間トークンなし → 中断")
                        print(f"\n  [TIMEOUT] {STALL_TIMEOUT}秒間応答なし → 中断")
                        break
                    continue

                last_activity = time.time()

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as e:
                    log.warning(f"  JSON解析失敗: {e} / raw: {line[:200]}")
                    continue

                content = chunk.get("message", {}).get("content", "")
                if content:
                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft = first_token_time - t_start
                        log.info(f"  最初のトークン到着: {ttft:.1f}秒")

                    token_count += 1
                    print(content, end="", flush=True)
                    result.append(content)

                    if detector.feed(content):
                        log.warning(f"  反復検出で中断: {detector.reason}")
                        print(f"\n  [ABORT] {detector.reason}")
                        break

                if chunk.get("done"):
                    break

    except requests.exceptions.ConnectionError:
        log.error(f"Ollamaに接続できません ({host})")
        raise RuntimeError(
            f"Ollamaに接続できません ({host})\n"
            "  → `ollama serve` が起動しているか確認してください"
        )
    except requests.exceptions.ReadTimeout:
        log.error(f"Ollamaタイムアウト ({timeout}秒)")
        print(f"\n  [TIMEOUT] {timeout}秒でタイムアウト")
    except Exception as e:
        log.error(f"Ollama API エラー: {type(e).__name__}: {e}")
        raise

    elapsed = time.time() - t_start
    output_text = "".join(result)
    log.info(f"  完了: {len(output_text)}文字, {token_count}トークン, {elapsed:.1f}秒")
    log.debug(f"  出力先頭200文字: {output_text[:200]}...")

    print()
    return output_text


def list_available_models(host: str) -> list[str]:
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def check_model_available(model: str, host: str) -> bool:
    models = list_available_models(host)
    return any(m == model or m.startswith(model.split(":")[0]) for m in models)


# ═════════════════════════════════════════════
# 後処理
# ═════════════════════════════════════════════

def strip_prompt_echo(text: str) -> str:
    """モデルがオウム返しした指示文を除去する"""
    kept = []
    skip_block = False
    for line in text.splitlines():
        stripped = line.strip()

        # プロンプトエコーブロックの開始検出
        if any(p in stripped for p in PROMPT_ECHO_PATTERNS):
            skip_block = True
            continue

        # エコーブロック終了: 普通の内容に戻ったら解除
        if skip_block:
            if stripped and not any(p in stripped for p in PROMPT_ECHO_PATTERNS):
                # まだ箇条書きっぽいエコーが続いている可能性
                if stripped.startswith("- ") and len(stripped) < 40:
                    continue
                skip_block = False
                kept.append(line)
            continue

        kept.append(line)

    return "\n".join(kept)


def trim_repeated_blocks(text: str) -> str:
    """後処理: 同一行・同一ブロックの反復を除去"""
    lines = text.splitlines()
    result = []
    prev_normalized = None
    repeat_count = 0

    for line in lines:
        normalized = re.sub(r"\s+", " ", line.strip())

        if normalized and normalized == prev_normalized:
            repeat_count += 1
            if repeat_count >= 2:
                # 3回目以降はスキップ（最大2回まで許容）
                continue
        else:
            prev_normalized = normalized
            repeat_count = 0 if not normalized else 1

        result.append(line)

    # ブロック単位の反復除去（セクション見出し+内容が繰り返されるパターン）
    text_out = "\n".join(result)
    text_out = _remove_repeated_sections(text_out)

    return text_out


def _remove_repeated_sections(text: str) -> str:
    """同一見出し+内容のセクションが繰り返されている場合、最初の1つだけ残す"""
    sections = re.split(r"(?=^#{1,4} )", text, flags=re.MULTILINE)
    seen_headings: dict[str, int] = {}
    kept = []

    for section in sections:
        # 見出し行を取り出す
        first_line = section.strip().split("\n")[0] if section.strip() else ""
        heading_normalized = re.sub(r"\s+", " ", first_line.strip())

        if heading_normalized.startswith("#"):
            if heading_normalized in seen_headings:
                seen_headings[heading_normalized] += 1
                if seen_headings[heading_normalized] > 1:
                    # 2回目以降は除去
                    continue
            else:
                seen_headings[heading_normalized] = 1

        kept.append(section)

    return "".join(kept)


def strip_empty_fences(text: str) -> str:
    """中身のないコードフェンスを除去"""
    return re.sub(r"(?:^|\n)```[^\n]*\n(?:\s*\n)*```(?:\n|$)", "\n", text)


def clean_dangling_fences(text: str) -> str:
    """対応の取れていないコードフェンスを除去"""
    lines = text.splitlines()
    fence_indices = [i for i, line in enumerate(lines) if re.match(r"^\s*```", line.strip())]

    if len(fence_indices) % 2 == 0:
        return text

    # 最後の孤立フェンスを除去
    last_fence = fence_indices[-1]
    return "\n".join(lines[:last_fence] + lines[last_fence + 1:])


def verify_placeholders(rewritten: str, protector: CodeBlockProtector) -> str:
    """プレースホルダが全て残っているか検証し、消えていたら末尾に追加"""
    missing = []
    for key in protector.blocks:
        if key not in rewritten:
            missing.append(key)

    if missing:
        print(f"  ⚠️  {len(missing)}個のコードブロックプレースホルダが消失。末尾に復元します")
        rewritten += "\n\n" + "\n\n".join(missing)

    return rewritten


def postprocess(text: str, protector: CodeBlockProtector) -> str:
    """リライト結果の後処理パイプライン"""
    text = strip_prompt_echo(text)
    text = trim_repeated_blocks(text)
    text = strip_empty_fences(text)
    text = clean_dangling_fences(text)
    text = verify_placeholders(text, protector)
    text = protector.restore(text)

    # 最終的な連続改行を整理
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ═════════════════════════════════════════════
# セクション分割
# ═════════════════════════════════════════════

def split_into_sections(text: str, max_chars: int = 2000) -> list[str]:
    """見出し単位で分割し、長すぎるものはさらに段落で再分割"""
    # まず見出しで分割
    parts = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)

    chunks = []
    current = ""

    for part in parts:
        if not part.strip():
            continue

        # チャンクサイズ内なら結合
        if len(current) + len(part) < max_chars:
            current += part
        else:
            if current.strip():
                chunks.append(current.strip())

            # 単一パートが大きすぎる場合は段落で再分割
            if len(part) > max_chars:
                sub_chunks = _split_by_paragraphs(part, max_chars)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = part

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    """段落単位で分割"""
    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= max_chars:
            current += ("\n\n" if current else "") + para
        else:
            if current.strip():
                chunks.append(current.strip())
            # 段落自体が大きすぎる場合（巨大なコードブロックプレースホルダなど）
            if len(para) > max_chars:
                chunks.append(para.strip())
                current = ""
            else:
                current = para

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ═════════════════════════════════════════════
# リライトプロンプト
# ═════════════════════════════════════════════

def build_rewrite_prompt(section: str, retry: bool = False) -> str:
    """本文リライト用プロンプトを構築"""
    lines = [
        "以下の記事本文をスタイルガイドに従ってリライトしてください。",
        "【CODE_BLOCK_N】のようなプレースホルダは絶対にそのまま残してください。",
        "本文のMarkdownだけを出力してください。",
    ]
    if retry:
        lines.append("前回は情報が大幅に欠落しました。原文の情報を一切省略せずリライトしてください。")

    return "\n".join(lines) + f"\n\n---\n{section}\n---"


def build_title_prompt(title: str) -> str:
    """タイトルリライト用プロンプトを構築"""
    return (
        "あなたはNote記事のタイトルを書き直す専門家です。\n"
        "以下のルールを必ず守ってください:\n\n"
        "1. AI臭い表現（「〜のすべて」「徹底解説」「完全ガイド」「〜とは？」）を除去\n"
        "2. 煽りすぎ・長すぎるタイトルは短くシンプルに\n"
        "3. 内容の核心が伝わる自然なタイトルにする\n"
        "4. 絵文字・装飾記号（【】など）は最小限に\n"
        "5. 出力はタイトル文字列1行のみ。#記号や説明は不要\n\n"
        f"元タイトル: {title}\n\n"
        "リライト後のタイトル:"
    )


# ═════════════════════════════════════════════
# メインのリライト処理
# ═════════════════════════════════════════════

def rewrite_article(
    article: dict,
    model: str,
    host: str,
    style_guide: str,
    rewrite_title: bool = True,
    chunk_size: int | None = None,
) -> str:
    """記事全体をリライトしてMarkdown文字列を返す"""
    title = article["title"]
    body = article["body_text"]
    url = article["url"]
    system = build_system_prompt(style_guide)

    effective_chunk = chunk_size if chunk_size else guess_chunk_size(model)
    print(f"\n[2/3] リライト開始 (model: {model}, chunk: {effective_chunk}文字)")
    log.info(f"リライト開始: model={model}, chunk={effective_chunk}, title=「{title}」")
    log.debug(f"本文全体: {len(body)}文字")

    # ── コードブロック保護 ──────────────────────
    protector = CodeBlockProtector()
    body_protected = protector.protect(body)

    log.info(f"{len(protector.blocks)}個のコードブロック/画像を保護")
    print(f"       → {len(protector.blocks)}個のコードブロック/画像を保護しました")

    # ── タイトルのリライト ──────────────────────
    t_title_elapsed = 0.0
    if rewrite_title:
        print("\n─── タイトルをリライト中 ───")
        log.info(f"タイトルリライト開始: 「{title}」")
        title_prompt = build_title_prompt(title)
        log.debug(f"タイトル用プロンプト:\n{title_prompt}")

        t_title_start = time.time()
        new_title = call_ollama(
            title_prompt, system, model, host
        ).strip()
        t_title_elapsed = time.time() - t_title_start

        # 前後の装飾を除去
        new_title = re.sub(r"^#+\s*", "", new_title)
        new_title = re.sub(r"^[「『【]|[」』】]$", "", new_title)
        new_title = new_title.split("\n")[0].strip()

        log.debug(f"タイトルLLM出力（整形後）: 「{new_title}」")

        # 元タイトルとほぼ同じ場合もフォールバック
        if (not new_title
                or len(new_title) > max(len(title) * 2, 100)
                or new_title == title):
            log.warning(f"タイトル変更なし/不安定 → 元タイトルを使用")
            print("  ⚠️  タイトル生成が不安定だったため、元タイトルを使います")
            new_title = title
        print(f"\n  変換: 「{title}」\n   → 「{new_title}」")
        print(f"  ⏱  タイトル生成: {t_title_elapsed:.1f}秒")
        log.info(f"タイトル確定: 「{new_title}」 ({t_title_elapsed:.1f}秒)")
    else:
        new_title = title
        log.info("タイトルリライトをスキップ")

    # ── 本文のリライト（セクション分割）──────────
    sections = split_into_sections(body_protected, max_chars=effective_chunk)
    rewritten_parts = []
    fallback_count = 0

    log.info(f"本文を{len(sections)}セクションに分割")
    for idx, sec in enumerate(sections, 1):
        log.debug(f"  セクション{idx}: {len(sec)}文字 / 先頭: {sec[:80]}...")

    section_times = []
    for i, section in enumerate(sections, 1):
        in_chars = len(section)
        print(f"\n─── セクション {i}/{len(sections)} ({in_chars}文字) ───")
        log.info(f"セクション {i}/{len(sections)} リライト開始 ({in_chars}文字)")

        prompt = build_rewrite_prompt(section)
        t_sec_start = time.time()
        rewritten = call_ollama(prompt, system, model, host)
        t_sec_elapsed = time.time() - t_sec_start
        out_chars = len(rewritten.strip())

        # スカスカ検出 + リトライ
        ratio = out_chars / in_chars if in_chars > 0 else 1.0
        log.info(f"  セクション{i} 結果: {out_chars}文字 (比率: {ratio:.0%}, {t_sec_elapsed:.1f}秒)")

        if ratio < 0.5 and in_chars > 50:
            log.warning(f"  セクション{i} 情報欠落の疑い ({ratio:.0%}) → リトライ")
            print(f"  ↺ 情報欠落の疑い ({ratio:.0%})。リトライします...")
            retry_prompt = build_rewrite_prompt(section, retry=True)
            t_retry_start = time.time()
            retried = call_ollama(retry_prompt, system, model, host)
            t_retry_elapsed = time.time() - t_retry_start
            t_sec_elapsed += t_retry_elapsed

            if len(retried.strip()) > len(rewritten.strip()):
                rewritten = retried
                out_chars = len(rewritten.strip())
                ratio = out_chars / in_chars if in_chars > 0 else 1.0
                log.info(f"  セクション{i} リトライ結果: {out_chars}文字 (比率: {ratio:.0%}, +{t_retry_elapsed:.1f}秒)")

        # それでもスカスカなら原文にフォールバック
        if ratio < 0.35 and in_chars > 50:
            log.warning(f"  セクション{i} フォールバック: 原文を使用 (比率: {ratio:.0%})")
            print(f"  ⚠️  スカスカ ({ratio:.0%}) → 原文をそのまま使用")
            rewritten_parts.append(section)
            fallback_count += 1
        else:
            rewritten_parts.append(rewritten)

        section_times.append(t_sec_elapsed)
        print(f"  ⏱  セクション{i}: {t_sec_elapsed:.1f}秒 ({in_chars}→{out_chars}文字)")

        if i < len(sections):
            time.sleep(0.3)

    if fallback_count:
        log.warning(f"{fallback_count}セクションでフォールバック発生")
        print(f"\n  ⚠️  {fallback_count}セクションでフォールバックが発生しました")

    # ── 後処理 ──────────────────────────────────
    body_rewritten = "\n\n".join(rewritten_parts)
    body_final = postprocess(body_rewritten, protector)

    md = f"# {new_title}\n\n"
    md += f"> 元記事: {url}\n\n"
    md += body_final

    # タイミング情報を返す
    timing = {
        "title_elapsed": t_title_elapsed if rewrite_title else 0.0,
        "section_times": section_times,
        "rewrite_title": rewrite_title,
    }
    return md, timing


# ═════════════════════════════════════════════
# フォーマット変換
# ═════════════════════════════════════════════

SUPPORTED_FORMATS = ["md", "txt", "html"]


def parse_formats(format_str: str) -> list[str]:
    """カンマ区切りのフォーマット文字列をパースして検証する"""
    formats = [f.strip().lower() for f in format_str.split(",")]
    invalid = [f for f in formats if f not in SUPPORTED_FORMATS]
    if invalid:
        raise ValueError(
            f"未対応のフォーマット: {', '.join(invalid)}\n"
            f"  対応フォーマット: {', '.join(SUPPORTED_FORMATS)}"
        )
    # 重複除去（順序維持）
    seen = set()
    unique = []
    for f in formats:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def md_to_txt(md_text: str) -> str:
    """Markdownをプレーンテキストに変換する"""
    text = md_text

    # 見出し: "## タイトル" → "■ タイトル" / "### タイトル" → "▼ タイトル"
    text = re.sub(r"^# (.+)$", r"━━━ \1 ━━━", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"■ \1", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.+)$", r"▼ \1", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,6} (.+)$", r"・\1", text, flags=re.MULTILINE)

    # 太字・斜体を除去
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # 取り消し線
    text = re.sub(r"~~(.+?)~~", r"\1", text)

    # リンク: [テキスト](URL) → テキスト (URL)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # 画像: ![alt](url) → [画像: alt] (url)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"[画像: \1] (\2)", text)

    # コードブロック: ``` → そのまま（インデントで表現）
    lines = text.split("\n")
    result = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                result.append("--- コード ---")
            else:
                in_code = False
                result.append("--------------")
            continue
        if in_code:
            result.append("    " + line)
        else:
            result.append(line)
    text = "\n".join(result)

    # インラインコード
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 引用
    text = re.sub(r"^> (.+)$", r"│ \1", text, flags=re.MULTILINE)

    # 水平線
    text = re.sub(r"^-{3,}$", "────────────────────────", text, flags=re.MULTILINE)

    # 箇条書きの記号を統一
    text = re.sub(r"^(\s*)\* ", r"\1・", text, flags=re.MULTILINE)

    return text


def md_to_html(md_text: str) -> str:
    """MarkdownをスタンドアロンHTMLに変換する"""
    # タイトルを抽出
    title_match = re.search(r"^# (.+)$", md_text, re.MULTILINE)
    page_title = title_match.group(1) if title_match else "Note記事"

    html_body = _convert_md_body_to_html(md_text)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(page_title)}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Kaku Gothic ProN",
                 "Noto Sans JP", "Yu Gothic", sans-serif;
    max-width: 780px;
    margin: 2rem auto;
    padding: 0 1.5rem;
    line-height: 1.85;
    color: #333;
    background: #fafafa;
  }}
  h1 {{ font-size: 1.7rem; border-bottom: 3px solid #49c6a3; padding-bottom: 0.5rem; }}
  h2 {{ font-size: 1.35rem; margin-top: 2.5rem; border-left: 4px solid #49c6a3; padding-left: 0.7rem; }}
  h3 {{ font-size: 1.15rem; margin-top: 2rem; color: #555; }}
  pre {{
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 1rem 1.2rem;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 0.9rem;
    line-height: 1.6;
  }}
  code {{
    background: #e8e8e8;
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  pre code {{
    background: none;
    padding: 0;
  }}
  blockquote {{
    border-left: 4px solid #ddd;
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    color: #666;
    background: #f5f5f5;
  }}
  a {{ color: #49c6a3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 2rem 0; }}
  ul, ol {{ padding-left: 1.5rem; }}
  li {{ margin-bottom: 0.3rem; }}
  img {{ max-width: 100%; height: auto; border-radius: 6px; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


def _escape_html(text: str) -> str:
    """HTMLエスケープ"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _convert_md_body_to_html(md_text: str) -> str:
    """Markdown本文をHTMLに変換する（簡易変換）"""
    lines = md_text.split("\n")
    html_parts: list[str] = []
    in_code = False
    in_list = False
    in_blockquote = False
    list_type = ""  # "ul" or "ol"

    i = 0
    while i < len(lines):
        line = lines[i]

        # コードブロック
        if line.strip().startswith("```"):
            if not in_code:
                _close_list(html_parts, in_list, list_type)
                in_list = False
                in_code = True
                html_parts.append("<pre><code>")
            else:
                in_code = False
                html_parts.append("</code></pre>")
            i += 1
            continue

        if in_code:
            html_parts.append(_escape_html(line))
            i += 1
            continue

        stripped = line.strip()

        # 空行
        if not stripped:
            if in_list:
                _close_list(html_parts, in_list, list_type)
                in_list = False
            if in_blockquote:
                html_parts.append("</blockquote>")
                in_blockquote = False
            i += 1
            continue

        # 見出し
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            if in_list:
                _close_list(html_parts, in_list, list_type)
                in_list = False
            level = len(heading_match.group(1))
            text = _inline_md_to_html(heading_match.group(2))
            html_parts.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # 水平線
        if re.match(r"^-{3,}$", stripped):
            if in_list:
                _close_list(html_parts, in_list, list_type)
                in_list = False
            html_parts.append("<hr>")
            i += 1
            continue

        # 引用
        if stripped.startswith("> "):
            if not in_blockquote:
                html_parts.append("<blockquote>")
                in_blockquote = True
            text = _inline_md_to_html(stripped[2:])
            html_parts.append(f"<p>{text}</p>")
            i += 1
            continue
        elif in_blockquote:
            html_parts.append("</blockquote>")
            in_blockquote = False

        # 箇条書き (- or *)
        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if ul_match:
            if not in_list or list_type != "ul":
                if in_list:
                    _close_list(html_parts, in_list, list_type)
                html_parts.append("<ul>")
                in_list = True
                list_type = "ul"
            text = _inline_md_to_html(ul_match.group(1))
            html_parts.append(f"<li>{text}</li>")
            i += 1
            continue

        # 番号付きリスト
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol_match:
            if not in_list or list_type != "ol":
                if in_list:
                    _close_list(html_parts, in_list, list_type)
                html_parts.append("<ol>")
                in_list = True
                list_type = "ol"
            text = _inline_md_to_html(ol_match.group(1))
            html_parts.append(f"<li>{text}</li>")
            i += 1
            continue

        # リスト終了判定
        if in_list:
            _close_list(html_parts, in_list, list_type)
            in_list = False

        # 通常の段落
        text = _inline_md_to_html(stripped)
        html_parts.append(f"<p>{text}</p>")
        i += 1

    # 末尾の閉じ処理
    if in_code:
        html_parts.append("</code></pre>")
    if in_list:
        _close_list(html_parts, in_list, list_type)
    if in_blockquote:
        html_parts.append("</blockquote>")

    return "\n".join(html_parts)


def _close_list(parts: list[str], in_list: bool, list_type: str):
    """リストタグを閉じる"""
    if in_list:
        parts.append(f"</{list_type}>")


def _inline_md_to_html(text: str) -> str:
    """インラインMarkdown要素をHTMLに変換"""
    # 画像
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        r'<img src="\2" alt="\1">',
        text,
    )
    # リンク
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # 太字
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # 斜体
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # 取り消し線
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    # インラインコード
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def convert_to_format(md_text: str, fmt: str) -> str:
    """Markdownテキストを指定フォーマットに変換する"""
    if fmt == "md":
        return md_text
    elif fmt == "txt":
        return md_to_txt(md_text)
    elif fmt == "html":
        return md_to_html(md_text)
    else:
        raise ValueError(f"未対応のフォーマット: {fmt}")


# ═════════════════════════════════════════════
# AI臭チェック（パターンマッチ方式）
# ═════════════════════════════════════════════

# チェック対象のAI臭パターン定義
# (パターン正規表現, 修正提案, カテゴリ)
AI_SMELL_PATTERNS: list[tuple[str, str, str]] = [
    # ── 全AI共通: 回りくどい表現 ──
    (r"〜と言えるでしょう|と言えるでしょう", "断定する（「〜だ」）か感想にする（「〜だと思う」）", "回りくどい表現"),
    (r"が求められます", "「〜が必要」に", "回りくどい表現"),
    (r"を実現しました", "「〜できた」に", "回りくどい表現"),
    (r"することが可能です", "「〜できる」に", "回りくどい表現"),
    (r"を活用することで", "「〜を使えば」に", "回りくどい表現"),
    (r"は非常に重要です", "「〜が大事」に", "回りくどい表現"),
    (r"を踏まえた上で", "「〜を考えると」に", "回りくどい表現"),
    (r"に焦点を当てて", "「〜について」に", "回りくどい表現"),
    (r"以上のことから", "「つまり」か削除", "回りくどい表現"),
    (r"することが(?:でき|重要|必要)", "冗長。短くする", "回りくどい表現"),
    (r"ということ(?:です|になります)", "「〜だ」「〜になる」に短縮", "回りくどい表現"),

    # ── 全AI共通: テンプレ構成 ──
    (r"本記事では.{0,10}(?:ご紹介|紹介|解説|説明)", "削除。いきなり本題に入る", "テンプレ構成"),
    (r"^(?:#+ )?はじめに\s*$", "不要。最初の段落が導入を兼ねる", "テンプレ構成"),
    (r"いかがでしたか", "削除。感想や次にやりたいことで締める", "テンプレ構成"),
    (r"それでは.{0,10}見ていきましょう", "削除", "テンプレ構成"),
    (r"について(?:解説|説明)(?:します|していきます)", "削除。そのまま書き始める", "テンプレ構成"),

    # ── 全AI共通: 煽りタイトル ──
    (r"徹底解説", "シンプルなタイトルに", "煽り表現"),
    (r"完全ガイド", "シンプルなタイトルに", "煽り表現"),
    (r"のすべて(?!が)", "シンプルなタイトルに", "煽り表現"),

    # ── ChatGPT特有 ──
    (r"素晴らしい(?:質問|ですね)", "削除", "ChatGPT的"),
    (r"以下に(?:まとめ|リスト|一覧)", "削除。リストが来るなら黙ってリストを書く", "ChatGPT的"),
    (r"お役に立てれば幸いです", "削除", "ChatGPT的"),
    (r"参考になれば幸いです", "削除", "ChatGPT的"),
    (r"ステップバイステップ", "「順番に」か削除", "ChatGPT的"),
    (r"具体的には以下の通りです", "削除", "ChatGPT的"),

    # ── Claude特有 ──
    (r"かもしれません[。、]", "確信があるなら断定する", "Claude的"),
    (r"と考えられます", "断定か「〜だと思う」に", "Claude的"),
    (r"いくつかの点を指摘", "そのまま指摘する", "Claude的"),
    (r"重要な点として", "普通に書く", "Claude的"),
    (r"注目に値します", "普通に書く", "Claude的"),

    # ── Gemini特有 ──
    (r"ポイントは\d+つ(?:あります|です)", "予告せずそのまま書く", "Gemini的"),
    (r"網羅的に", "削除", "Gemini的"),
    (r"包括的に", "削除", "Gemini的"),

    # ── Grok特有 ──
    (r"ぶっちゃけ", "文体に合わせて調整", "Grok的"),
]

# 文末パターン検出用
SENTENCE_END_RE = re.compile(r"[。！？\n]")


def check_ai_smell(text: str) -> list[dict]:
    """
    テキストからAI臭パターンを検出して結果リストを返す。
    各要素: {line_num, line_text, match, suggestion, category}
    """
    findings: list[dict] = []
    lines = text.split("\n")

    # コードブロック内はスキップ
    in_code = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        for pattern, suggestion, category in AI_SMELL_PATTERNS:
            for m in re.finditer(pattern, line):
                findings.append({
                    "line_num": line_num,
                    "line_text": line.strip(),
                    "match": m.group(),
                    "suggestion": suggestion,
                    "category": category,
                })

    # ── 文末パターンの単調さチェック ──
    endings = _extract_sentence_endings(text)
    monotone = _check_monotone_endings(endings)
    if monotone:
        findings.extend(monotone)

    # ── 接続詞の過剰使用チェック ──
    conjunction_issues = _check_conjunctions(text)
    if conjunction_issues:
        findings.extend(conjunction_issues)

    return findings


def _extract_sentence_endings(text: str) -> list[str]:
    """文末表現を抽出する"""
    # 文末の「〜です。」「〜ます。」「〜た。」等を取り出す
    endings = []
    for m in re.finditer(r"([ぁ-ん]{1,6})[。！？]", text):
        endings.append(m.group(1))
    return endings


def _check_monotone_endings(endings: list[str]) -> list[dict]:
    """文末の単調さをチェック"""
    issues = []
    if len(endings) < 4:
        return issues

    # 3連続以上の同一文末を検出
    for i in range(len(endings) - 2):
        if endings[i] == endings[i + 1] == endings[i + 2]:
            issues.append({
                "line_num": 0,
                "line_text": f"文末「〜{endings[i]}」が3回以上連続",
                "match": f"〜{endings[i]}",
                "suggestion": "文末を散らす（「〜だった」「〜してみた」「〜かな」等）",
                "category": "文末の単調さ",
            })
            break  # 1件だけ報告

    return issues


def _check_conjunctions(text: str) -> list[dict]:
    """接続詞の過剰使用をチェック"""
    issues = []
    conj_pattern = r"(?:しかし|また|さらに|したがって|一方で|ただし|そのため|それゆえ|加えて)"

    paragraphs = re.split(r"\n{2,}", text)
    for para in paragraphs:
        matches = re.findall(conj_pattern, para)
        if len(matches) >= 3:
            first_line = para.strip().split("\n")[0][:50]
            issues.append({
                "line_num": 0,
                "line_text": f"段落「{first_line}...」",
                "match": "、".join(matches),
                "suggestion": "接続詞を減らす。段落の切り替えで文脈を伝える",
                "category": "接続詞の過剰使用",
            })

    return issues


def format_deai_report(findings: list[dict], title: str, char_count: int) -> str:
    """AI臭チェック結果をMarkdownレポートに整形する"""
    report = []
    report.append(f"# AI臭チェックレポート")
    report.append(f"\n> 対象: 「{title}」({char_count}文字)")
    report.append(f"> チェック日: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    if not findings:
        report.append("## 結果: 問題なし")
        report.append("")
        report.append("AI臭パターンは検出されませんでした。")
        return "\n".join(report)

    # カテゴリ別に分類
    by_category: dict[str, list[dict]] = {}
    for f in findings:
        cat = f["category"]
        by_category.setdefault(cat, []).append(f)

    report.append(f"## 検出: {len(findings)}箇所")
    report.append("")

    # サマリーテーブル（リスト形式、Note互換）
    report.append("**カテゴリ別サマリー:**")
    report.append("")
    for cat, items in by_category.items():
        report.append(f"- **{cat}**: {len(items)}件")
    report.append("")

    # 詳細
    report.append("---")
    report.append("")
    idx = 1
    for cat, items in by_category.items():
        report.append(f"### {cat}")
        report.append("")
        for item in items:
            line_info = f"(L{item['line_num']})" if item["line_num"] > 0 else ""
            report.append(f"**{idx}.** `{item['match']}` {line_info}")
            if item["line_num"] > 0:
                # 行テキストは長すぎたら切る
                lt = item["line_text"]
                if len(lt) > 80:
                    lt = lt[:80] + "..."
                report.append(f"   原文: {lt}")
            report.append(f"   → {item['suggestion']}")
            report.append("")
            idx += 1

    # スコア（簡易）
    report.append("---")
    report.append("")
    score = max(0, 100 - len(findings) * 5)
    if score >= 80:
        grade = "良好（軽微な修正で済む）"
    elif score >= 50:
        grade = "要改善（AI臭が目立つ箇所あり）"
    else:
        grade = "要大幅修正（AI臭が強い）"

    report.append(f"### 簡易スコア: {score}/100 — {grade}")
    report.append("")

    return "\n".join(report)


def run_deai_check(article: dict, output_path: str | None = None) -> str:
    """AI臭チェックを実行してレポートを返す"""
    title = article["title"]
    body = article["body_text"]

    print(f"\n[deai] AI臭チェック開始: 「{title}」({len(body)}文字)")

    findings = check_ai_smell(body)

    # タイトルもチェック（本文の # 見出しとは別にタイトル単体を検査）
    title_findings = check_ai_smell(title)
    for f in title_findings:
        f["line_text"] = f"タイトル: {title}"
        f["line_num"] = 0
        f["category"] = "タイトル"
    # 本文の1行目が「# タイトル」のときに重複するので、本文側の1行目見出しの煽り系は除外
    findings = [
        f for f in findings
        if not (f["line_num"] == 1 and f["line_text"].startswith("# ") and f["category"] == "煽り表現")
    ]
    findings = title_findings + findings

    report = format_deai_report(findings, title, len(body))

    if findings:
        print(f"  → {len(findings)}箇所のAI臭パターンを検出")
    else:
        print(f"  → AI臭パターンは検出されませんでした")

    # ファイル保存
    if output_path:
        out_p = Path(output_path)
    else:
        filename_base = safe_filename(title)
        out_p = Path(f"{filename_base}_deai.md")

    out_p.write_text(report, encoding="utf-8")
    print(f"  [REPORT] {out_p.resolve()}")

    return report


# ═════════════════════════════════════════════
# 記事評価
# ═════════════════════════════════════════════

EVAL_SYSTEM_PROMPT = """\
あなたは日本語Webライティングの専門評価者です。
Note(note.com) 記事を以下の観点で厳密に評価してください。
出力はMarkdown形式で、指定されたフォーマットに厳密に従ってください。
"""


def build_eval_prompt(title: str, body: str) -> str:
    """記事評価用プロンプトを構築"""
    return f"""\
以下のNote記事を評価してください。

## 評価対象
タイトル: {title}

本文:
---
{body[:6000]}
---

## 出力フォーマット（厳守）

### 総合スコア: NN/100

### 評価内訳

**文章品質 (NN/25)**
- AI臭: (強い / やや感じる / ほぼない)
- 読みやすさ: (1文が長すぎる / 適切 / テンポが良い)
- 文体の一貫性: (ブレあり / 概ね統一 / 完全に統一)
- 冗長さ: (冗長 / やや冗長 / 簡潔)
- 具体的な問題箇所を2-3個引用して指摘

**構成・導線 (NN/25)**
- タイトル: (弱い / 普通 / 引きが強い)
- 導入（最初の3行）: (弱い / 普通 / 引き込まれる)
- 見出し構成: (不適切 / 普通 / わかりやすい)
- CTA・まとめ: (なし / 弱い / 効果的)
- 改善すべき構成上の問題を指摘

**SEO・発見性 (NN/25)**
- タイトルのキーワード: (不足 / 普通 / 最適)
- 見出しへのキーワード配置: (不足 / 普通 / 最適)
- 記事の長さ: (短すぎ / 適切 / 長すぎ)
- 改善すべきSEOの問題を指摘

**Note最適化 (NN/25)**
- Markdown互換性: (問題あり / 概ねOK / 完全対応)
- 段落の長さ（スマホ閲覧）: (長すぎ / 適切 / 最適)
- 画像・コードの配置: (不適切 / 普通 / 効果的)
- 改善すべきNote固有の問題を指摘

### 改善提案（優先度順）

1. 【最重要】...
2. 【重要】...
3. 【推奨】...
4. 【あれば良い】...
5. 【あれば良い】...
"""


def build_compare_eval_prompt(
    title_orig: str, body_orig: str,
    title_new: str, body_new: str,
) -> str:
    """リライト前後の比較評価用プロンプト"""
    return f"""\
以下のNote記事について、リライト前（原文）とリライト後（修正文）を比較評価してください。

## 原文
タイトル: {title_orig}

本文:
---
{body_orig[:4000]}
---

## 修正文
タイトル: {title_new}

本文:
---
{body_new[:4000]}
---

## 出力フォーマット（厳守）

### リライト評価サマリー

| 観点 | 原文 | 修正文 | 変化 |
|------|------|--------|------|
| 総合スコア | NN/100 | NN/100 | +NN |
| 文章品質 | NN/25 | NN/25 | +NN |
| 構成・導線 | NN/25 | NN/25 | +NN |
| SEO・発見性 | NN/25 | NN/25 | +NN |
| Note最適化 | NN/25 | NN/25 | +NN |

### 改善された点
- ...（具体的に原文→修正文の変化を引用して説明、3-5個）

### まだ改善の余地がある点
- ...（修正文でもまだ残っている問題、2-3個）

### リライトで悪化した点（あれば）
- ...（原文の方が良かった箇所。なければ「特になし」）

### 次のアクション（優先度順）
1. ...
2. ...
3. ...
"""


def evaluate_article(
    article: dict,
    model: str,
    host: str,
    rewritten_md: str | None = None,
    rewritten_title: str | None = None,
) -> tuple[str, float]:
    """記事を評価してMarkdownレポートを返す"""
    title = article["title"]
    body = article["body_text"]

    if rewritten_md and rewritten_title:
        # リライト前後の比較評価
        print("\n─── リライト前後の比較評価中 ───")
        log.info("比較評価モード: 原文 vs リライト後")
        prompt = build_compare_eval_prompt(
            title, body, rewritten_title, rewritten_md,
        )
    else:
        # 単体評価
        print("\n─── 記事の評価中 ───")
        log.info("単体評価モード")
        prompt = build_eval_prompt(title, body)

    t_eval_start = time.time()
    eval_result = call_ollama(
        prompt, EVAL_SYSTEM_PROMPT, model, host,
        temperature=0.3, timeout=600,
    )
    t_eval_elapsed = time.time() - t_eval_start

    print(f"\n  ⏱  評価生成: {t_eval_elapsed:.1f}秒")
    log.info(f"評価完了: {len(eval_result)}文字, {t_eval_elapsed:.1f}秒")

    return eval_result, t_eval_elapsed


def build_eval_report(
    article: dict,
    eval_result: str,
    rewritten_md: str | None = None,
) -> str:
    """評価レポートのMarkdownを組み立てる"""
    title = article["title"]
    url = article["url"]
    body = article["body_text"]

    report = []
    report.append(f"# 📝 記事評価レポート")
    report.append(f"\n> 対象記事: [{title}]({url})")
    report.append(f"> 評価日: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    # 評価結果
    report.append("---")
    report.append("")
    report.append(eval_result.strip())
    report.append("")

    # 原文
    report.append("---")
    report.append("")
    report.append("## 原文")
    report.append("")
    report.append(f"### {title}")
    report.append("")
    # 長すぎる場合は先頭部分のみ
    if len(body) > 5000:
        report.append(body[:5000])
        report.append(f"\n\n*（以下省略… 全{len(body)}文字）*")
    else:
        report.append(body)
    report.append("")

    # 修正文（リライトした場合）
    if rewritten_md:
        report.append("---")
        report.append("")
        report.append("## 修正文（リライト後）")
        report.append("")
        if len(rewritten_md) > 5000:
            report.append(rewritten_md[:5000])
            report.append(f"\n\n*（以下省略… 全{len(rewritten_md)}文字）*")
        else:
            report.append(rewritten_md)
        report.append("")

    return "\n".join(report)


# ═════════════════════════════════════════════
# ファイル名生成
# ═════════════════════════════════════════════

def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|【】「」『』（）()、。！？\s]+', "_", title)
    return name.strip("_")[:60] or "note_article"


# ═════════════════════════════════════════════
# エントリポイント
# ═════════════════════════════════════════════

def main():
    global log

    parser = argparse.ArgumentParser(
        description="Note記事をローカルLLMで自分の文体にリライトするツール (v4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python note_rewriter.py https://note.com/zephel01/n/n1fce90d35555
  python note_rewriter.py article_draft.md
  python note_rewriter.py article_draft.md --deai
  python note_rewriter.py https://note.com/zephel01/n/nXXX --model qwen3.5:9b
  python note_rewriter.py https://note.com/zephel01/n/nXXX --template my_style.md
  python note_rewriter.py https://note.com/zephel01/n/nXXX --format txt
  python note_rewriter.py https://note.com/zephel01/n/nXXX --format md,txt,html
  python note_rewriter.py https://note.com/zephel01/n/nXXX --dry-run
  python note_rewriter.py https://note.com/zephel01/n/nXXX --evaluate
  python note_rewriter.py https://note.com/zephel01/n/nXXX --evaluate-only
        """
    )
    parser.add_argument("source", help="NoteのURL または ローカルの .md/.txt ファイルパス")
    parser.add_argument("--template", default=None,
                        help="文体テンプレートファイル (例: style_template.md)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollamaモデル名 (デフォルト: {DEFAULT_MODEL}、環境変数 NOTE_REWRITER_MODEL で変更可)")
    parser.add_argument("--output", default=None,
                        help="出力先のベースパス (拡張子は --format に合わせて自動付与)")
    parser.add_argument("--format", default=DEFAULT_FORMAT, dest="formats",
                        help=f"出力形式: md, txt, html (カンマ区切りで複数指定可。デフォルト: {DEFAULT_FORMAT}、環境変数 NOTE_REWRITER_FORMAT で変更可)")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"OllamaホストURL (デフォルト: {DEFAULT_HOST}、環境変数 NOTE_REWRITER_HOST で変更可)")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR,
                        help=f"ログ出力先ディレクトリ (デフォルト: {DEFAULT_LOG_DIR}、環境変数 NOTE_REWRITER_LOG_DIR で変更可)")
    parser.add_argument("--dry-run", action="store_true",
                        help="LLMを呼ばず原文だけ表示して終了")
    parser.add_argument("--no-title", action="store_true",
                        help="タイトルはリライトしない")
    parser.add_argument("--evaluate", action="store_true",
                        help="記事の完成度を評価するレポートを生成する")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="リライトせず評価レポートのみ生成する")
    parser.add_argument("--chunk-size", type=int, default=None,
                        help="1回のLLM呼び出しに渡す最大文字数 "
                             "(デフォルト: モデルサイズから自動推定)")
    parser.add_argument("--deai", action="store_true",
                        help="AI臭チェック＆修正提案モード (LLMリライトなし、パターンマッチ検出)")
    args = parser.parse_args()

    # ── ロガー初期化 ──────────────────────────────
    log = setup_logger(args.log_dir)
    log.info("=" * 60)
    log.info(f"note_rewriter v4 起動")
    log.info(f"  source: {args.source}")
    log.info(f"  model: {args.model}")
    log.info(f"  format: {args.formats}")
    log.info(f"  host: {args.host}")
    log.info(f"  template: {args.template or '(auto/default)'}")
    log.info(f"  chunk-size: {args.chunk_size or '(auto)'}")
    log.info(f"  evaluate: {args.evaluate or args.evaluate_only}")
    log.info(f"  deai: {args.deai}")
    log.info("=" * 60)

    # フォーマットのバリデーション
    try:
        output_formats = parse_formats(args.formats)
    except ValueError as e:
        log.error(f"フォーマットエラー: {e}")
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent

    # ── ソース取得（URL or ローカルファイル）────────
    source_is_url = is_url(args.source)
    t_fetch_start = time.time()
    try:
        if source_is_url:
            article = fetch_article(args.source)
        else:
            article = load_local_file(args.source)
        t_fetch_elapsed = time.time() - t_fetch_start
        log.info(f"ソース取得成功: 「{article['title']}」({len(article['body_text'])}文字, {t_fetch_elapsed:.1f}秒)")
        print(f"  ⏱  ソース取得: {t_fetch_elapsed:.1f}秒")
    except Exception as e:
        log.error(f"ソース取得失敗: {e}")
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    # ── テンプレート読み込み ──────────────────────
    style_guide = load_template(args.template, script_dir)
    log.debug(f"テンプレート内容:\n{style_guide[:500]}...")

    # ── dry-run ──────────────────────────────────
    if args.dry_run:
        protector = CodeBlockProtector()
        body_protected = protector.protect(article["body_text"])
        sections = split_into_sections(
            body_protected,
            max_chars=args.chunk_size or guess_chunk_size(args.model),
        )

        print("\n" + "=" * 60)
        print(f"# {article['title']}")
        print("=" * 60)
        print(article["body_text"])
        print(f"\n[保護されるコードブロック: {len(protector.blocks)}個]")
        print(f"[セクション分割数: {len(sections)}]")
        for i, sec in enumerate(sections, 1):
            print(f"  セクション{i}: {len(sec)}文字")
        print("\n[使用テンプレート]")
        print(style_guide[:400] + "..." if len(style_guide) > 400 else style_guide)
        print("\n[dry-run完了] LLMは呼ばずに終了します")
        log.info("dry-run完了")
        sys.exit(0)

    # ── deaiモード（LLM不要）───────────────────────
    if args.deai:
        log.info("deaiモード: AI臭チェック開始")
        output_path = None
        if args.output:
            output_path = args.output
        run_deai_check(article, output_path=output_path)
        total_elapsed = time.time() - t_fetch_start
        print(f"\n✅ AI臭チェック完了！ ({total_elapsed:.1f}秒)")
        log.info(f"deaiモード完了: {total_elapsed:.1f}秒")
        sys.exit(0)

    # ── Ollama接続確認 ───────────────────────────
    print(f"\n[check] Ollamaに接続中 ({args.host})...")
    log.info(f"Ollama接続確認: {args.host}")
    models = list_available_models(args.host)
    if not models:
        log.error(f"Ollamaに接続できません: {args.host}")
        print(
            f"[ERROR] Ollamaに接続できません。\n"
            f"  → `ollama serve` で起動してください\n"
            f"  → ホスト: {args.host}",
            file=sys.stderr
        )
        sys.exit(1)

    log.info(f"利用可能モデル: {', '.join(models)}")

    if not check_model_available(args.model, args.host):
        log.warning(f"モデル '{args.model}' なし → pull開始")
        print(f"\n[INFO] モデル '{args.model}' がありません。ダウンロードを試みます...")
        print(f"  利用可能: {', '.join(models)}")
        import subprocess
        try:
            subprocess.run(["ollama", "pull", args.model], check=True)
        except Exception as e:
            log.error(f"pull失敗: {e}")
            print(f"[ERROR] pullに失敗: {e}", file=sys.stderr)
            print(f"  手動で実行してください: ollama pull {args.model}")
            sys.exit(1)

    print(f"  → モデル '{args.model}' 準備OK")

    effective_chunk = args.chunk_size if args.chunk_size else guess_chunk_size(args.model)
    print(f"  → チャンクサイズ: {effective_chunk}文字", end="")
    if not args.chunk_size:
        print(f" (モデル名から自動推定)", end="")
    print()

    # ── evaluate-only モード ─────────────────────
    if args.evaluate_only:
        print(f"\n[1/1] 記事の評価中...")
        t_total_start = time.time()
        eval_result, t_eval_elapsed = evaluate_article(
            article, args.model, args.host,
        )
        total_elapsed = time.time() - t_total_start

        report = build_eval_report(article, eval_result)
        filename_base = safe_filename(article["title"])
        if args.output:
            report_path = Path(args.output).with_suffix(".md")
        else:
            report_path = Path(f"{filename_base}_eval.md")
        report_path.write_text(report, encoding="utf-8")
        log.info(f"評価レポート保存: {report_path.resolve()}")
        print(f"\n  [REPORT] {report_path.resolve()}")

        # サマリー
        print(f"\n{'─' * 50}")
        print(f"⏱  処理時間サマリー")
        print(f"{'─' * 50}")
        print(f"  モデル:         {args.model}")
        print(f"  記事取得:       {t_fetch_elapsed:.1f}秒")
        print(f"  評価生成:       {t_eval_elapsed:.1f}秒")
        print(f"  ────────────────────")
        print(f"  合計:           {total_elapsed:.1f}秒")
        print(f"{'─' * 50}")
        print(f"\n✅ 評価レポート完了！ ({total_elapsed:.1f}秒)")
        log.info(f"evaluate-only完了: {total_elapsed:.1f}秒")
        sys.exit(0)

    # ── リライト ────────────────────────────────
    t_total_start = time.time()
    rewrite_title_flag = not args.no_title
    try:
        rewritten_md, timing = rewrite_article(
            article, args.model, args.host, style_guide,
            rewrite_title=rewrite_title_flag,
            chunk_size=args.chunk_size,
        )
    except RuntimeError as e:
        log.error(f"リライト失敗: {e}")
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    t_title_total = timing["title_elapsed"]
    section_times_summary = timing["section_times"]

    # ── 評価（--evaluate 付きの場合）──────────────
    t_eval_elapsed = 0.0
    eval_report_path = None
    if args.evaluate:
        # リライト後のタイトルを抽出
        rewritten_title = article["title"]
        first_line = rewritten_md.strip().split("\n")[0]
        if first_line.startswith("# "):
            rewritten_title = first_line[2:].strip()

        eval_result, t_eval_elapsed = evaluate_article(
            article, args.model, args.host,
            rewritten_md=rewritten_md,
            rewritten_title=rewritten_title,
        )
        report = build_eval_report(article, eval_result, rewritten_md=rewritten_md)
        filename_base_eval = safe_filename(article["title"])
        eval_report_path = Path(f"{filename_base_eval}_eval.md")
        eval_report_path.write_text(report, encoding="utf-8")
        log.info(f"評価レポート保存: {eval_report_path.resolve()}")
        print(f"\n  [REPORT] {eval_report_path.resolve()}")

    total_elapsed = time.time() - t_total_start
    log.info(f"リライト総時間: {total_elapsed:.1f}秒")

    # ── 保存 ────────────────────────────────────
    filename_base = safe_filename(article["title"])

    if args.output:
        base = Path(args.output).with_suffix("")
    else:
        base = Path(f"{filename_base}_rewritten")

    print(f"\n[保存中] (フォーマット: {', '.join(output_formats)})")

    saved_files = []
    for fmt in output_formats:
        out_path = base.with_suffix(f".{fmt}")
        t_conv_start = time.time()
        converted = convert_to_format(rewritten_md, fmt)
        t_conv_elapsed = time.time() - t_conv_start
        out_path.write_text(converted, encoding="utf-8")
        saved_files.append((fmt, out_path, len(converted), t_conv_elapsed))
        log.info(f"保存: [{fmt.upper()}] {out_path.resolve()} ({len(converted)}文字, 変換{t_conv_elapsed:.2f}秒)")
        print(f"  [{fmt.upper()}] {out_path.resolve()} ({len(converted)}文字, 変換{t_conv_elapsed:.2f}秒)")

    # ── サマリー表示 ──────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"⏱  処理時間サマリー")
    print(f"{'─' * 50}")
    print(f"  モデル:         {args.model}")
    print(f"  記事取得:       {t_fetch_elapsed:.1f}秒")
    if rewrite_title_flag:
        print(f"  タイトル生成:   {t_title_total:.1f}秒")
    for i, st in enumerate(section_times_summary, 1):
        print(f"  セクション{i}:    {st:.1f}秒")
    if args.evaluate:
        print(f"  記事評価:       {t_eval_elapsed:.1f}秒")
    for fmt, _, _, ct in saved_files:
        print(f"  {fmt.upper()}変換:        {ct:.2f}秒")
    print(f"  ────────────────────")
    print(f"  合計:           {total_elapsed:.1f}秒")
    print(f"{'─' * 50}")

    file_count = len(saved_files) + (1 if eval_report_path else 0)
    log.info(f"全処理完了: {file_count}ファイル, 総時間{total_elapsed:.1f}秒")
    print(f"\n✅ 完了！ ({file_count}ファイル保存, {total_elapsed:.1f}秒)")


if __name__ == "__main__":
    main()
