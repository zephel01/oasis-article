#!/usr/bin/env python3
"""
エッジデバイス SLM ベンチマークスクリプト（ハイブリッド版）
============================================================
速度・メモリ  → llama-bench で GGUF を直接実行（正確な生値）
日本語RAG品質 → Ollama API（対応モデル）+ llama-simple（Bonsai）

GGUF ファイルは ~/llm/models/ に直接配置する。
Ollama のマニフェスト/blob は使わない（権限・パス問題を回避）。

対応デバイス：Raspberry Pi 5 / Jetson Orin Nano Super

使い方：
  # 1. 事前準備
  pip install requests psutil --break-system-packages

  # 2. GGUF モデルを ~/llm/models/ に配置
  mkdir -p ~/llm/models
  # Bonsai: https://huggingface.co/prism-ml/Bonsai-1.7B-gguf
  # LFM2.5-JP: https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP-GGUF
  # LFM2.5-350M: ollama pull sam860/lfm2.5:350m → ollama cp でエクスポート
  # Gemma 4: ollama pull gemma4:e2b → ollama cp でエクスポート

  # 3. llama.cpp ビルド（通常版）
  git clone https://github.com/ggml-org/llama.cpp ~/llm/apps/llama.cpp
  cd ~/llm/apps/llama.cpp
  # CPU: cmake -B build -G Ninja && cmake --build build --config Release -j$(nproc)
  # Jetson CUDA:
  cmake -B build -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87 \
    -DGGML_CUDA_F16=ON -DGGML_CUDA_FA_ALL_QUANTS=ON
  cmake --build build --config Release -j6

  # 4. PrismML fork ビルド（Bonsai用）
  git clone https://github.com/Mintplex-Labs/prism-ml-llama.cpp ~/llm/apps/prism-ml-llama.cpp
  cd ~/llm/apps/prism-ml-llama.cpp
  cmake -B build -G Ninja  # CPU版。CUDA版は上記と同じオプション
  cmake --build build --config Release -j$(nproc)

  # 5. 実行
  python3 benchmark_slm.py
  python3 benchmark_slm.py --device "Jetson Orin Nano Super (8GB)"
  python3 benchmark_slm.py --models-dir /path/to/gguf/files
"""

import json
import csv
import time
import os
import sys
import re
import subprocess
import argparse
import glob
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List

try:
    import requests
except ImportError:
    print("Error: requests が必要です。pip install requests --break-system-packages")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("Error: psutil が必要です。pip install psutil --break-system-packages")
    sys.exit(1)


# ==============================================================================
# 設定
# ==============================================================================

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# GGUF モデルディレクトリ（~/llm/models/ にGGUFファイルを直接配置）
def _find_gguf_models_dir() -> str:
    """GGUF モデルディレクトリを自動検出"""
    candidates = [
        os.path.expanduser("~/llm/models"),
        os.path.expanduser("~/models"),
        os.path.expanduser("~"),
    ]
    for p in candidates:
        if os.path.isdir(p) and any(f.endswith(".gguf") for f in os.listdir(p)):
            return p
    return os.path.expanduser("~/llm/models")

GGUF_MODELS_DIR = _find_gguf_models_dir()

# llama.cpp パス（環境に合わせて変更）
def _find_llama_cpp_dir(*names: str) -> str:
    """llama.cpp ディレクトリを探す。複数の候補名を受け取る"""
    for name in names:
        candidates = [
            os.path.expanduser(f"~/llm/apps/{name}"),
            os.path.expanduser(f"~/{name}"),
            f"/opt/{name}",
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
    return os.path.expanduser(f"~/{names[0]}")  # デフォルト

LLAMA_CPP_DIR = _find_llama_cpp_dir("llama.cpp")
PRISM_LLAMA_CPP_DIR = _find_llama_cpp_dir("prism-ml-llama.cpp", "prism-llama.cpp")

# 検証対象モデル
# gguf_filename: ~/llm/models/ 内の GGUF ファイル名
# ollama_name:   Ollama API 用のモデル名（RAG テスト・フォールバック速度計測に使用）
# use_prism:     True なら PrismML fork の llama-bench を使用
MODELS = [
    {
        "ollama_name": "bonsai-1.7b",
        "gguf_filename": "Bonsai-1.7B.gguf",
        "display": "Bonsai-1.7B",
        "category": "1-bit超軽量",
        "use_prism": True,
    },
    {
        "ollama_name": "sam860/lfm2.5:350m",
        "gguf_filename": "LFM2.5-350M*.gguf",  # glob パターン対応
        "display": "LFM2.5-350M",
        "category": "超軽量エッジ",
        "use_prism": False,
    },
    {
        "ollama_name": "lfm25-jp",
        "gguf_filename": "LFM2.5-1.2B-JP*.gguf",  # Q4_K_M 等のサフィックス対応
        "display": "LFM2.5-1.2B-JP",
        "category": "日本語特化",
        "use_prism": False,
    },
    {
        "ollama_name": "gemma4:e2b",
        "gguf_filename": "gemma-4-E2B*.gguf",
        "display": "Gemma 4 E2B",
        "category": "マルチモーダル",
        "use_prism": False,
    },
    {
        "ollama_name": "gemma4:e4b",
        "gguf_filename": "gemma-4-E4B*.gguf",
        "display": "Gemma 4 E4B",
        "category": "マルチモーダル高精度",
        "use_prism": False,
    },
]

# llama-bench パラメータ
BENCH_PROMPT_TOKENS = [128, 256, 512]  # pp (prompt processing) テスト
BENCH_GEN_TOKENS = [128, 256]          # tg (text generation) テスト

# 日本語RAGテスト
RAG_TESTS = [
    {
        "id": "fact_1",
        "category": "事実抽出",
        "context": (
            "東京スカイツリーは2012年5月22日に開業した。"
            "高さは634mで、自立式電波塔としては世界一の高さを誇る。"
            "所在地は東京都墨田区押上一丁目。"
        ),
        "question": "東京スカイツリーの高さは何メートルですか？数字だけで答えてください。",
        "expected_keywords": ["634"],
        "strict": True,
    },
    {
        "id": "fact_2",
        "category": "事実抽出",
        "context": (
            "富士山は標高3,776mの日本最高峰の山である。"
            "2013年にユネスコの世界文化遺産に登録された。"
            "静岡県と山梨県にまたがる。"
        ),
        "question": "富士山が世界文化遺産に登録されたのは何年ですか？数字だけで答えてください。",
        "expected_keywords": ["2013"],
        "strict": True,
    },
    {
        "id": "fact_3",
        "category": "事実抽出",
        "context": (
            "日本の首都は東京都である。人口は約1,400万人。"
            "23の特別区、26の市、5つの町、8つの村から構成されている。"
        ),
        "question": "東京都の特別区の数はいくつですか？数字だけで答えてください。",
        "expected_keywords": ["23"],
        "strict": True,
    },
    {
        "id": "summary_1",
        "category": "要約",
        "context": (
            "近年、大規模言語モデルの小型化が急速に進んでいる。"
            "2024年以降、1B〜3Bクラスのモデルでも実用的な性能を発揮し、"
            "スマートフォンやRaspberry Piなどのエッジデバイスでの動作が現実的になった。"
            "特に量子化技術の進歩で、メモリ使用量は大幅に削減された。"
            "2026年には1-bit量子化モデルも登場し、"
            "1.7Bモデルがわずか0.24GBで動作するようになった。"
        ),
        "question": "上記の文章を1〜2文で要約してください。",
        "expected_keywords": ["小型化", "エッジ", "量子化"],
        "strict": False,
    },
    {
        "id": "reasoning_1",
        "category": "推論",
        "context": (
            "以下の3つのモデルから、メモリ4GB以下で日本語チャットボットを構築する最適なモデルを選んでください。\n"
            "A: モデルX - メモリ8GB、日本語精度95%、速度10 tok/s\n"
            "B: モデルY - メモリ0.5GB、日本語精度80%、速度200 tok/s\n"
            "C: モデルZ - メモリ3GB、日本語精度90%、速度50 tok/s"
        ),
        "question": "メモリ4GB以下という条件で最適なモデルはどれですか？アルファベット1文字で答えてください。",
        "expected_keywords": ["C"],
        "strict": True,
    },
]

# 計測回数
NUM_RUNS = 3

# 出力
OUTPUT_CSV = "benchmark_results.csv"
OUTPUT_JSON = "benchmark_results.json"


# ==============================================================================
# ユーティリティ
# ==============================================================================

def print_header(text: str):
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def print_sub(text: str):
    print(f"\n--- {text} ---")


def _find_binary(base_dir: str, name: str) -> Optional[str]:
    """llama.cpp のバイナリを探す（build/bin/ 優先）"""
    candidates = [
        os.path.join(base_dir, "build", "bin", name),
        os.path.join(base_dir, "bin", name),
        os.path.join(base_dir, name),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # glob で探す（Ninja や別ビルドディレクトリ対応）
    pattern = os.path.join(base_dir, "**", name)
    found = glob.glob(pattern, recursive=True)
    if found:
        return found[0]
    return None


def detect_gpu() -> dict:
    """NVIDIA GPU 検出"""
    info = {"available": False, "name": "", "vram_total_mb": 0, "vram_used_mb": 0}
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = r.stdout.strip().split(",")
            info["available"] = True
            info["name"] = parts[0].strip()
            # Jetson等の統合メモリ環境では [N/A] が返る
            try:
                info["vram_total_mb"] = int(parts[1].strip())
            except (ValueError, IndexError):
                info["vram_total_mb"] = 0
            try:
                info["vram_used_mb"] = int(parts[2].strip())
            except (ValueError, IndexError):
                info["vram_used_mb"] = 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return info


def detect_device() -> dict:
    """デバイス自動検出"""
    info = {"type": "unknown", "cpu": "", "ram_gb": 0}
    try:
        mem = psutil.virtual_memory()
        info["ram_gb"] = round(mem.total / (1024**3), 1)
        r = subprocess.run(["cat", "/proc/cpuinfo"], capture_output=True, text=True, timeout=5)
        if "BCM2712" in r.stdout or "Raspberry Pi" in r.stdout:
            info["type"] = "Raspberry Pi 5"
        elif "NVIDIA" in r.stdout or "Cortex-A78AE" in r.stdout:
            info["type"] = "Jetson Orin Nano"
        for line in r.stdout.split("\n"):
            if "model name" in line.lower():
                info["cpu"] = line.split(":")[-1].strip()
                break
    except Exception:
        pass
    return info


# ==============================================================================
# GGUF パス解決（ファイル直接指定）
# ==============================================================================

def resolve_gguf_path(gguf_filename: str) -> Optional[str]:
    """
    GGUF_MODELS_DIR 内から GGUF ファイルを探す。
    glob パターン対応（例: "LFM2.5-1.2B-JP*.gguf"）。
    """
    # 完全一致
    exact = os.path.join(GGUF_MODELS_DIR, gguf_filename)
    if os.path.isfile(exact):
        return exact

    # glob パターン
    pattern = os.path.join(GGUF_MODELS_DIR, gguf_filename)
    matches = glob.glob(pattern)
    if matches:
        # サイズ最大のものを選択（同名モデルの異なる量子化がある場合）
        matches.sort(key=os.path.getsize, reverse=True)
        return matches[0]

    # GGUF_MODELS_DIR 内を再帰検索（サブディレクトリ対応）
    pattern_recursive = os.path.join(GGUF_MODELS_DIR, "**", gguf_filename)
    matches = glob.glob(pattern_recursive, recursive=True)
    if matches:
        matches.sort(key=os.path.getsize, reverse=True)
        return matches[0]

    print(f"  [WARN] GGUF 未発見: {gguf_filename} in {GGUF_MODELS_DIR}")
    return None


# ==============================================================================
# Part 1: llama-bench による速度・メモリ計測
# ==============================================================================

def run_llama_bench(
    gguf_path: str,
    use_prism: bool = False,
    gpu_layers: int = 99,
    prompt_tokens: int = 128,
    gen_tokens: int = 128,
) -> dict:
    """
    llama-bench を実行して結果をパースする。
    返り値: {"pp_tok_s": float, "tg_tok_s": float, "model_size_gb": float}
    """
    # llama-bench バイナリ選択
    base_dir = PRISM_LLAMA_CPP_DIR if use_prism else LLAMA_CPP_DIR
    bench_bin = _find_binary(base_dir, "llama-bench")
    if not bench_bin:
        return {"error": f"llama-bench 未発見: {base_dir}/build/bin/ を確認してください"}

    gpu_info = detect_gpu()
    ngl = gpu_layers if gpu_info["available"] else 0

    cmd = [
        bench_bin,
        "-m", gguf_path,
        "-p", str(prompt_tokens),
        "-n", str(gen_tokens),
        "-ngl", str(ngl),
        "-r", str(NUM_RUNS),
        "-o", "json",
    ]

    print(f"  実行: {bench_bin} -p {prompt_tokens} -n {gen_tokens} -ngl {ngl}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[-500:] if result.stderr else "不明"
            return {"error": f"llama-bench 失敗 (code={result.returncode}):\n{stderr}"}

        # JSON 出力をパース
        output = result.stdout.strip()
        data = parse_bench_output(output)
        return data

    except subprocess.TimeoutExpired:
        return {"error": "タイムアウト（600秒）"}
    except Exception as e:
        return {"error": str(e)}


def parse_bench_output(output: str) -> dict:
    """
    llama-bench の JSON 出力をパースする（修正版）。

    対応フォーマット：
    1. JSON配列形式: [...] - 複数オブジェクト
    2. JSONL形式: 1行1オブジェクト

    各オブジェクトから avg_ts を抽出し、n_prompt/n_gen で分類。
    """
    results = {"pp_tok_s": 0, "tg_tok_s": 0, "model_size_gb": 0}

    pp_values = []
    tg_values = []
    parsed_lines = 0

    # JSON配列形式か JSONL形式かを判定
    output = output.strip()
    if not output:
        results["parse_failed"] = True
        print(f"  [WARN] llama-bench 出力が空です")
        return results

    entries = []
    try:
        # まず全体を JSON 配列として解析
        if output.startswith("["):
            entries = json.loads(output)
            print(f"  [DEBUG] JSON配列形式で{len(entries)}個のエントリを検出")
        else:
            # JSONL形式の場合は行ごとに解析
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    if line and not line.startswith("{") and not line.startswith("["):
                        print(f"  [DEBUG] llama-bench non-JSON: {line[:100]}")
                    continue
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON パース失敗: {e}")
        results["parse_failed"] = True
        return results

    # 各エントリから情報を抽出
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        parsed_lines += 1

        # モデルサイズ（最初のエントリから取得）
        if "model_size" in entry and not results["model_size_gb"]:
            model_size = entry.get("model_size", 0)
            if model_size:
                results["model_size_gb"] = round(model_size / (1024**3), 2)

        # n_prompt / n_gen キーで判定
        n_prompt = entry.get("n_prompt", 0)
        n_gen = entry.get("n_gen", 0)
        avg_ts = entry.get("avg_ts", 0)

        if n_prompt > 0 and avg_ts > 0:  # Prefill テスト
            pp_values.append(avg_ts)
        elif n_gen > 0 and avg_ts > 0:  # Generation テスト
            tg_values.append(avg_ts)

    # 平均値を計算
    if pp_values:
        results["pp_tok_s"] = round(sum(pp_values) / len(pp_values), 2)
    if tg_values:
        results["tg_tok_s"] = round(sum(tg_values) / len(tg_values), 2)

    # パース結果の判定
    if parsed_lines == 0:
        results["parse_failed"] = True
        print(f"  [WARN] llama-bench JSON パース失敗（0行解析）")
    elif results["pp_tok_s"] == 0 and results["tg_tok_s"] == 0:
        results["parse_failed"] = True
        print(f"  [WARN] llama-bench パース成功({parsed_lines}行)だが全値0 → 非対応モデルの可能性")
    else:
        print(f"  [OK] llama-bench パース成功: pp={results['pp_tok_s']} tg={results['tg_tok_s']} tok/s")

    return results


def get_memory_during_bench(gguf_path: str, use_prism: bool, ngl: int) -> dict:
    """
    llama-bench 実行中の RAM + GPU VRAM を計測する。
    llama-bench を別プロセスで起動し、その間にメモリをサンプリング。
    llama-cli の対話モード問題を回避。
    """
    base_dir = PRISM_LLAMA_CPP_DIR if use_prism else LLAMA_CPP_DIR
    bench_bin = _find_binary(base_dir, "llama-bench")
    if not bench_bin:
        return {"ram_peak_mb": 0, "gpu_peak_mb": 0}

    cmd = [
        bench_bin,
        "-m", gguf_path,
        "-p", "32",
        "-n", "32",
        "-ngl", str(ngl),
        "-r", "1",
        "-o", "json",
    ]

    ram_samples = []
    gpu_samples = []
    max_wait = 120  # 最大120秒

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL
    )

    start = time.time()
    try:
        while proc.poll() is None:
            if time.time() - start > max_wait:
                proc.kill()
                break

            # RAM: llama-bench プロセスの RSS を取得
            try:
                p = psutil.Process(proc.pid)
                ram_mb = p.memory_info().rss / (1024 * 1024)
                # 子プロセスも合算
                for child in p.children(recursive=True):
                    try:
                        ram_mb += child.memory_info().rss / (1024 * 1024)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                ram_samples.append(ram_mb)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # GPU
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0:
                    val = r.stdout.strip()
                    if val and val != "[N/A]":
                        gpu_samples.append(float(val))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            time.sleep(0.5)

        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    return {
        "ram_peak_mb": round(max(ram_samples), 1) if ram_samples else 0,
        "gpu_peak_mb": round(max(gpu_samples), 1) if gpu_samples else 0,
    }


def speed_test_ollama(model_name: str, num_predict: int = 128) -> dict:
    """
    Ollama API で速度テスト（llama-bench 失敗時のフォールバック）。
    Ollama の /api/generate レスポンスに含まれる eval_count / eval_duration から tok/s を算出。
    """
    prompt = "日本の四季について、それぞれの特徴を説明してください。"
    try:
        print(f"  [DEBUG] Ollama API コール: POST {OLLAMA_BASE_URL}/api/generate")
        print(f"  [DEBUG] model={model_name}, num_predict={num_predict}")

        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": num_predict, "temperature": 0.0},
            },
            timeout=600,
        )

        print(f"  [DEBUG] Response status: {r.status_code}")

        if r.status_code != 200:
            print(f"  [WARN] Ollama API エラー: {r.status_code}")
            print(f"  [DEBUG] Response: {r.text[:200]}")
            return {"error": f"Ollama API エラー: {r.status_code}"}

        data = r.json()

        # Ollama レスポンスから速度情報を取得
        eval_count = data.get("eval_count", 0)
        eval_duration = data.get("eval_duration", 0)  # ナノ秒
        prompt_eval_count = data.get("prompt_eval_count", 0)
        prompt_eval_duration = data.get("prompt_eval_duration", 0)  # ナノ秒

        print(f"  [DEBUG] eval_count={eval_count}, eval_duration={eval_duration}ns")
        print(f"  [DEBUG] prompt_eval_count={prompt_eval_count}, prompt_eval_duration={prompt_eval_duration}ns")

        tg_tok_s = (eval_count / (eval_duration / 1e9)) if eval_duration > 0 else 0
        pp_tok_s = (prompt_eval_count / (prompt_eval_duration / 1e9)) if prompt_eval_duration > 0 else 0

        print(f"  [OK] Ollama 速度: pp={pp_tok_s:.2f} tg={tg_tok_s:.2f} tok/s")

        return {
            "pp_tok_s": round(pp_tok_s, 2),
            "tg_tok_s": round(tg_tok_s, 2),
            "eval_count": eval_count,
            "source": "ollama_api",
        }
    except requests.ConnectionError as e:
        print(f"  [ERROR] Ollama に接続できません: {OLLAMA_BASE_URL}")
        return {"error": f"Ollama 接続失敗: {e}"}
    except requests.Timeout as e:
        print(f"  [ERROR] Ollama API タイムアウト")
        return {"error": f"Ollama API タイムアウト: {e}"}
    except Exception as e:
        print(f"  [ERROR] Ollama API 失敗: {e}")
        return {"error": f"Ollama API 失敗: {e}"}


def memory_test_ollama(model_name: str) -> dict:
    """Ollama 推論中のメモリ使用量を計測（llama-bench 失敗時のフォールバック）"""
    ram_samples = []
    gpu_samples = []

    def sample_memory():
        for p in psutil.process_iter(["name", "cmdline", "memory_info"]):
            try:
                name = p.info.get("name", "").lower()
                cmdline = " ".join(p.info.get("cmdline", []) or []).lower()
                if "ollama" in name or "ollama" in cmdline:
                    ram_samples.append(p.info["memory_info"].rss / (1024 * 1024))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                val = r.stdout.strip()
                if val and val != "[N/A]":
                    gpu_samples.append(float(val))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # プリロード
    try:
        requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model_name, "prompt": "test", "stream": False,
                  "options": {"num_predict": 1}},
            timeout=300,
        )
    except Exception:
        pass

    # サンプリング（推論しながら）
    import threading
    stop_event = threading.Event()

    def sampler():
        while not stop_event.is_set():
            sample_memory()
            time.sleep(0.5)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    try:
        requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model_name, "prompt": "日本の歴史について詳しく説明してください。",
                  "stream": False, "options": {"num_predict": 100}},
            timeout=300,
        )
    except Exception:
        pass

    stop_event.set()
    t.join(timeout=5)

    return {
        "ram_peak_mb": round(max(ram_samples), 1) if ram_samples else 0,
        "gpu_peak_mb": round(max(gpu_samples), 1) if gpu_samples else 0,
        "source": "ollama_api",
    }


# ==============================================================================
# Part 2: 日本語RAG品質テスト
# ==============================================================================

def rag_test_ollama(model_name: str, test: dict) -> dict:
    """Ollama API でRAGテスト"""
    is_thinking_model = "gemma" in model_name.lower()

    prompt = (
        f"以下のコンテキストに基づいて質問に答えてください。簡潔に回答のみ出力してください。\n\n"
        f"コンテキスト:\n{test['context']}\n\n"
        f"質問: {test['question']}"
    )
    # thinking モデル向けに num_predict を大幅に増やす（thinking 分を含む）
    num_predict = 1024 if is_thinking_model else 100

    # thinking モデルの場合、/no_think テンプレートを使って thinking を抑制
    # Ollama >=0.9 で対応: options に think=false を指定
    options = {"num_predict": num_predict, "temperature": 0.0}
    if is_thinking_model:
        options["num_ctx"] = 4096  # thinking 分のコンテキスト確保

    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        # thinking 抑制: think パラメータ（Ollama >=0.9）
        if is_thinking_model:
            payload["think"] = False

        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=600,
        )
        answer = r.json().get("response", "").strip()
    except Exception as e:
        answer = f"ERROR: {e}"

    return evaluate_rag(test, answer)


def _is_garbage_output(answer: str) -> bool:
    """llama-simple の出力がゴミ（CLI引数のエコー等）かどうか判定"""
    if not answer:
        return True
    # CLI引数パターンの繰り返し
    if re.match(r'^-[a-z]', answer) and ('-ngl' in answer or '-n ' in answer):
        return True
    # 同じトークンの無限繰り返し（例: "0000000..." や "9999999..."）
    if len(answer) > 20 and len(set(answer.replace(" ", ""))) <= 3:
        return True
    return False


def rag_test_llama_cli(gguf_path: str, use_prism: bool, test: dict, ngl: int,
                       model_name: str = "") -> dict:
    """llama-simple でRAGテスト（Bonsai用）。llama-cli は対話モードに入るため使わない。
    ゴミ出力の場合は Ollama API にフォールバック。"""
    base_dir = PRISM_LLAMA_CPP_DIR if use_prism else LLAMA_CPP_DIR

    # llama-simple を優先（対話モードなし、生成後に確実に終了）
    # 見つからなければ llama-cli にフォールバック
    cli_bin = _find_binary(base_dir, "llama-simple")
    if not cli_bin:
        cli_bin = _find_binary(base_dir, "llama-cli")
    if not cli_bin:
        # llama-simple 未発見 → Ollama API フォールバック
        if model_name:
            print(f"  [FALLBACK] llama-simple 未発見 → Ollama API")
            return rag_test_ollama(model_name, test)
        return {"test_id": test["id"], "category": test["category"],
                "answer": f"ERROR: llama-simple/llama-cli 未発見 ({base_dir})",
                "keywords_found": [], "score": 0}

    prompt = (
        f"以下のコンテキストに基づいて質問に答えてください。簡潔に回答のみ出力してください。\n\n"
        f"コンテキスト:\n{test['context']}\n\n"
        f"質問: {test['question']}\n\n回答:"
    )

    cmd = [
        cli_bin, "-m", gguf_path,
        "-p", prompt,
        "-n", "256",
        "-ngl", str(ngl),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=120, stdin=subprocess.DEVNULL,
        )
        # llama-simple はプロンプトも出力するため、プロンプト部分を除去
        raw = result.stdout
        if "回答:" in raw:
            answer = raw.split("回答:")[-1].strip()
        else:
            answer = raw.strip()
    except subprocess.TimeoutExpired:
        answer = "ERROR: タイムアウト（120秒）"
    except Exception as e:
        answer = f"ERROR: {e}"

    # ゴミ出力検出 → Ollama API フォールバック
    if _is_garbage_output(answer) and model_name:
        print(f"  [FALLBACK] llama-simple ゴミ出力検出 → Ollama API")
        return rag_test_ollama(model_name, test)

    return evaluate_rag(test, answer)


def strip_thinking(text: str) -> str:
    """Gemma 4 等の <think>...</think> タグを除去して本文のみ返す"""
    # <think>...</think> を除去（複数・ネスト対応）
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text)
    # 閉じタグなしの <think>... も除去（生成が途中で切れた場合）
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned)
    return cleaned.strip()


def evaluate_rag(test: dict, answer: str) -> dict:
    """RAG回答を評価"""
    # thinking トークンを除去してから評価
    answer_clean = strip_thinking(answer)
    keywords_found = [kw for kw in test["expected_keywords"] if kw in answer_clean]

    if test["strict"]:
        score = 1.0 if len(keywords_found) == len(test["expected_keywords"]) else 0.0
    else:
        score = len(keywords_found) / max(len(test["expected_keywords"]), 1)

    return {
        "test_id": test["id"],
        "category": test["category"],
        "answer": answer_clean[:200] if answer_clean else f"(thinking only) {answer[:100]}",
        "keywords_found": keywords_found,
        "score": score,
    }


# ==============================================================================
# メイン
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="エッジデバイス SLM ベンチマーク")
    parser.add_argument("--device", type=str, default=None, help="デバイス名")
    parser.add_argument("--models-dir", type=str, default=None, help="GGUF モデルディレクトリ")
    parser.add_argument("--llama-cpp", type=str, default=None, help="llama.cpp パス")
    parser.add_argument("--prism-cpp", type=str, default=None, help="PrismML llama.cpp パス")
    parser.add_argument("--skip-bench", action="store_true", help="速度テストをスキップ")
    parser.add_argument("--skip-rag", action="store_true", help="RAGテストをスキップ")
    args = parser.parse_args()

    global LLAMA_CPP_DIR, PRISM_LLAMA_CPP_DIR, GGUF_MODELS_DIR
    if args.models_dir is not None:
        GGUF_MODELS_DIR = args.models_dir
    if args.llama_cpp is not None:
        LLAMA_CPP_DIR = args.llama_cpp
    if args.prism_cpp is not None:
        PRISM_LLAMA_CPP_DIR = args.prism_cpp

    device_info = detect_device()
    device_name = args.device or f"{device_info['type']} ({device_info['ram_gb']}GB)"
    gpu_info = detect_gpu()

    print_header("エッジデバイス SLM ベンチマーク（ハイブリッド版）")
    print(f"デバイス: {device_name}")
    print(f"RAM: {device_info['ram_gb']} GB")
    if gpu_info["available"]:
        print(f"GPU: {gpu_info['name']} (VRAM: {gpu_info['vram_total_mb']}MB)")
    else:
        print("GPU: なし（CPU推論）")
    print(f"GGUF models: {GGUF_MODELS_DIR}")
    print(f"llama.cpp:   {LLAMA_CPP_DIR}")
    print(f"PrismML:     {PRISM_LLAMA_CPP_DIR}")
    print(f"開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    ngl = 99 if gpu_info["available"] else 0
    all_results = []

    for model in MODELS:
        ollama_name = model["ollama_name"]
        gguf_filename = model["gguf_filename"]
        display = model["display"]
        use_prism = model["use_prism"]

        print_header(f"テスト中: {display} ({ollama_name})")

        result = {
            "model_name": ollama_name,
            "display_name": display,
            "category": model["category"],
            "timestamp": datetime.now().isoformat(),
        }

        # GGUF パス解決（ファイル直接指定）
        gguf = resolve_gguf_path(gguf_filename)
        if gguf:
            size_mb = round(os.path.getsize(gguf) / (1024 * 1024), 1)
            print(f"  GGUF: {gguf}")
            print(f"  サイズ: {size_mb} MB")
            print(f"  推論: {'PrismML fork' if use_prism else 'llama.cpp'} (ngl={ngl})")
        else:
            print(f"  [INFO] GGUF 未発見: {gguf_filename} → Ollama API のみで計測")

        # ==== 速度テスト ====
        if not args.skip_bench:
            print_sub("速度テスト（llama-bench）")
            bench_results = []
            bench_all_failed = True

            # GGUF がある場合のみ llama-bench を実行
            if gguf:
                for pp in BENCH_PROMPT_TOKENS:
                    for tg in BENCH_GEN_TOKENS:
                        br = run_llama_bench(gguf, use_prism, ngl, pp, tg)
                        br["pp_tokens"] = pp
                        br["tg_tokens"] = tg
                        bench_results.append(br)
                        if "error" in br:
                            print(f"  [ERROR] pp={pp} tg={tg}: {br['error']}")
                        elif br.get("parse_failed"):
                            print(f"  [WARN] pp={pp} tg={tg}: llama-bench 結果が全て0（非対応モデル?）")
                        else:
                            bench_all_failed = False
                            print(f"  pp={pp} tg={tg}: prefill={br['pp_tok_s']} tok/s, decode={br['tg_tok_s']} tok/s")
                        # 最初の1つが失敗 or 全て0なら残りもスキップ
                        if bench_all_failed and len(bench_results) == 1:
                            break
                    if bench_all_failed and len(bench_results) == 1:
                        break
            else:
                print("  GGUF なし → llama-bench スキップ")

            # llama-bench 全滅 or GGUF なし → Ollama API フォールバック
            if bench_all_failed:
                print(f"  [FALLBACK] Ollama API で速度計測")
                for num_pred in [50, 128, 256]:
                    sr = speed_test_ollama(ollama_name, num_pred)
                    if "error" in sr:
                        print(f"  [ERROR] Ollama n={num_pred}: {sr['error']}")
                    else:
                        print(f"  Ollama n={num_pred}: prefill={sr['pp_tok_s']} tok/s, decode={sr['tg_tok_s']} tok/s")
                        bench_results.append(sr)
                        bench_all_failed = False

            result["bench_results"] = bench_results

            # 代表値を抽出
            if not bench_all_failed:
                def _is_valid(b):
                    return ("error" not in b and not b.get("parse_failed")
                            and (b.get("pp_tok_s", 0) > 0 or b.get("tg_tok_s", 0) > 0))

                # llama-bench の代表値（pp=256, tg=128）を優先
                rep = next(
                    (b for b in bench_results
                     if b.get("pp_tokens") == 256 and b.get("tg_tokens") == 128 and _is_valid(b)),
                    None,
                )
                # なければ有効な結果から（Ollama フォールバック含む）
                if not rep:
                    rep = next((b for b in bench_results if _is_valid(b)), {})
                result["pp_tok_s"] = rep.get("pp_tok_s", 0)
                result["tg_tok_s"] = rep.get("tg_tok_s", 0)
            else:
                result["pp_tok_s"] = 0
                result["tg_tok_s"] = 0

            # メモリ計測
            print_sub("メモリ計測")
            # llama-bench で有効な結果が得られたか判定
            has_valid_bench = gguf and any(
                "error" not in b and not b.get("parse_failed")
                and b.get("pp_tokens") and (b.get("pp_tok_s", 0) > 0 or b.get("tg_tok_s", 0) > 0)
                for b in bench_results
            )
            if has_valid_bench:
                mem = get_memory_during_bench(gguf, use_prism, ngl)
            else:
                # GGUF なし or llama-bench 使えない → Ollama API 経由で計測
                print("  （Ollama API 経由で計測）")
                mem = memory_test_ollama(ollama_name)
            result["ram_peak_mb"] = mem["ram_peak_mb"]
            result["gpu_peak_mb"] = mem["gpu_peak_mb"]
            print(f"  RAM ピーク: {mem['ram_peak_mb']} MB")
            if gpu_info["available"]:
                print(f"  GPU VRAM ピーク: {mem['gpu_peak_mb']} MB")
        else:
            print("  [SKIP] 速度テスト省略")

        # ==== RAGテスト ====
        if not args.skip_rag:
            print_sub("日本語RAGテスト")
            rag_results = []

            for test in RAG_TESTS:
                print(f"  {test['category']} ({test['id']})...", end=" ")

                if use_prism and gguf:
                    # Bonsai: llama-simple で実行（ゴミ出力時は Ollama フォールバック）
                    rr = rag_test_llama_cli(gguf, use_prism, test, ngl, model_name=ollama_name)
                else:
                    # Ollama API（GGUF なしの場合も含む）
                    rr = rag_test_ollama(ollama_name, test)

                rag_results.append(rr)
                mark = "✓" if rr["score"] >= 0.5 else "✗"
                print(f"{mark} score={rr['score']:.1f} | {rr['answer'][:50]}...")

            result["rag_results"] = rag_results
        else:
            print("  [SKIP] RAGテスト省略")

        all_results.append(result)

    # ======================================================================
    # 結果出力
    # ======================================================================
    print_header("結果サマリー")

    # CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "モデル", "カテゴリ",
            "Prefill(tok/s)", "Decode(tok/s)",
            "RAM_Peak(MB)", "GPU_Peak(MB)",
            "RAG_事実抽出(%)", "RAG_要約(%)", "RAG_推論(%)",
            "エラー",
        ])
        for r in all_results:
            rag_by_cat = {}
            for rr in r.get("rag_results", []):
                cat = rr["category"]
                rag_by_cat.setdefault(cat, []).append(rr["score"])

            def pct(cat):
                s = rag_by_cat.get(cat, [])
                return f"{round(sum(s)/max(len(s),1)*100)}%" if s else "-"

            w.writerow([
                r["display_name"], r["category"],
                r.get("pp_tok_s", "-"), r.get("tg_tok_s", "-"),
                r.get("ram_peak_mb", "-"), r.get("gpu_peak_mb", "-"),
                pct("事実抽出"), pct("要約"), pct("推論"),
                r.get("error", ""),
            ])
    print(f"  CSV: {OUTPUT_CSV}")

    # JSON
    json_out = {
        "benchmark_info": {
            "device": device_name,
            "device_detect": device_info,
            "gpu": gpu_info,
            "gguf_models_dir": GGUF_MODELS_DIR,
            "llama_cpp": LLAMA_CPP_DIR,
            "prism_cpp": PRISM_LLAMA_CPP_DIR,
            "timestamp": datetime.now().isoformat(),
            "num_runs": NUM_RUNS,
        },
        "results": all_results,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {OUTPUT_JSON}")

    # コンソール表示
    print_header("速度比較（代表値: pp=256, tg=128）")
    print(f"{'モデル':<20} {'Prefill':>12} {'Decode':>12} {'RAM':>10} {'GPU':>10}")
    print("-" * 66)
    for r in all_results:
        pp = r.get("pp_tok_s", "-")
        tg = r.get("tg_tok_s", "-")
        ram = r.get("ram_peak_mb", "-")
        gpu = r.get("gpu_peak_mb", "-")
        pp_s = f"{pp} tok/s" if isinstance(pp, (int, float)) else str(pp)
        tg_s = f"{tg} tok/s" if isinstance(tg, (int, float)) else str(tg)
        ram_s = f"{ram}MB" if isinstance(ram, (int, float)) else str(ram)
        gpu_s = f"{gpu}MB" if isinstance(gpu, (int, float)) and gpu > 0 else "-"
        err = r.get("error", "")
        if err:
            print(f"{r['display_name']:<20} {'ERROR':>12} {err}")
        else:
            print(f"{r['display_name']:<20} {pp_s:>12} {tg_s:>12} {ram_s:>10} {gpu_s:>10}")

    print_header("日本語RAG品質")
    print(f"{'モデル':<20} {'事実抽出':>10} {'要約':>10} {'推論':>10}")
    print("-" * 52)
    for r in all_results:
        rag_by_cat = {}
        for rr in r.get("rag_results", []):
            cat = rr["category"]
            rag_by_cat.setdefault(cat, []).append(rr["score"])

        def pct(cat):
            s = rag_by_cat.get(cat, [])
            return f"{round(sum(s)/max(len(s),1)*100)}%" if s else "N/A"

        print(f"{r['display_name']:<20} {pct('事実抽出'):>10} {pct('要約'):>10} {pct('推論'):>10}")

    print(f"\n完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
