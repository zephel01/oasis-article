#!/usr/bin/env python3
"""
heic_to_png.py — HEICファイルをまとめてPNGに変換するスクリプト

使い方:
  python heic_to_png.py                           # カレントディレクトリの全HEIC
  python heic_to_png.py ~/Pictures                 # 指定ディレクトリ
  python heic_to_png.py photo1.heic photo2.HEIC    # 個別ファイル
  python heic_to_png.py -o output/ ~/Pictures      # 出力先を指定
  python heic_to_png.py --width 1920               # 長辺1920pxにリサイズ
  python heic_to_png.py --scale 50                 # 50%に縮小
  python heic_to_png.py --max-filesize 500         # 500KB以下に収める
  python heic_to_png.py -r ~/Pictures              # サブディレクトリも再帰的に
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    from PIL import Image
    import pillow_heif
except ImportError:
    print("[ERROR] 必要なライブラリがありません。以下を実行してください:")
    print("  pip install pillow pillow-heif")
    sys.exit(1)

# pillow_heif を Pillow に登録
pillow_heif.register_heif_opener()


# ═════════════════════════════════════════════
# 環境変数で上書きできるデフォルト設定
# ═════════════════════════════════════════════

DEFAULT_WIDTH = int(os.environ.get("HEIC_PNG_WIDTH", "0"))         # 0 = リサイズなし
DEFAULT_SCALE = int(os.environ.get("HEIC_PNG_SCALE", "0"))         # 0 = スケールなし
DEFAULT_MAX_FILESIZE = int(os.environ.get("HEIC_PNG_MAX_KB", "0")) # 0 = 制限なし
DEFAULT_QUALITY = int(os.environ.get("HEIC_PNG_QUALITY", "9"))     # PNG圧縮レベル 0-9


def collect_heic_files(paths: list[str], recursive: bool) -> list[Path]:
    """引数からHEICファイルのリストを収集する"""
    heic_files = []
    heic_exts = {".heic", ".heif"}

    for p in paths:
        path = Path(p)
        if path.is_file():
            if path.suffix.lower() in heic_exts:
                heic_files.append(path)
            else:
                print(f"  [SKIP] HEICファイルではありません: {path}")
        elif path.is_dir():
            if recursive:
                for ext in heic_exts:
                    heic_files.extend(sorted(path.rglob(f"*{ext}")))
                    heic_files.extend(sorted(path.rglob(f"*{ext.upper()}")))
            else:
                for ext in heic_exts:
                    heic_files.extend(sorted(path.glob(f"*{ext}")))
                    heic_files.extend(sorted(path.glob(f"*{ext.upper()}")))
        else:
            print(f"  [SKIP] 見つかりません: {path}")

    # 重複排除（大文字小文字の拡張子で二重に拾う場合がある）
    seen = set()
    unique = []
    for f in heic_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(f)

    return unique


def resize_image(img: Image.Image, width: int, scale: int) -> Image.Image:
    """画像をリサイズする（width=長辺px、scale=パーセント）"""
    if scale > 0:
        new_w = int(img.width * scale / 100)
        new_h = int(img.height * scale / 100)
        return img.resize((new_w, new_h), Image.LANCZOS)

    if width > 0:
        # 長辺を指定pxに合わせる（アスペクト比維持）
        long_side = max(img.width, img.height)
        if long_side <= width:
            return img  # 元画像が指定サイズ以下ならそのまま
        ratio = width / long_side
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        return img.resize((new_w, new_h), Image.LANCZOS)

    return img


def save_with_filesize_limit(
    img: Image.Image, out_path: Path, max_kb: int, compress_level: int
) -> int:
    """ファイルサイズ制限付きでPNG保存。収まらない場合は段階的に縮小する"""
    # まずそのまま保存を試みる
    img.save(out_path, "PNG", compress_level=compress_level)
    file_kb = out_path.stat().st_size // 1024

    if max_kb <= 0 or file_kb <= max_kb:
        return file_kb

    # 段階的に縮小してファイルサイズを合わせる
    current_img = img
    for scale_pct in [90, 80, 70, 60, 50, 40, 30, 20]:
        new_w = int(img.width * scale_pct / 100)
        new_h = int(img.height * scale_pct / 100)
        if new_w < 16 or new_h < 16:
            break
        current_img = img.resize((new_w, new_h), Image.LANCZOS)
        current_img.save(out_path, "PNG", compress_level=compress_level)
        file_kb = out_path.stat().st_size // 1024
        if file_kb <= max_kb:
            return file_kb

    return file_kb


def convert_heic_to_png(
    heic_path: Path,
    output_dir: Path | None,
    width: int,
    scale: int,
    max_filesize_kb: int,
    compress_level: int,
) -> tuple[bool, str]:
    """1ファイルを変換する。(成功, メッセージ) を返す"""
    try:
        img = Image.open(heic_path)

        # EXIF回転を適用
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img) or img

        # RGBAをRGBに変換（透明度がない場合）
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        original_size = f"{img.width}x{img.height}"

        # リサイズ
        img = resize_image(img, width, scale)
        new_size = f"{img.width}x{img.height}"

        # 出力パス
        if output_dir:
            out_path = output_dir / (heic_path.stem + ".png")
        else:
            out_path = heic_path.with_suffix(".png")

        # 同名ファイルが存在する場合は連番
        if out_path.exists():
            i = 1
            while True:
                candidate = out_path.with_stem(f"{heic_path.stem}_{i}")
                if not candidate.exists():
                    out_path = candidate
                    break
                i += 1

        # 保存
        file_kb = save_with_filesize_limit(img, out_path, max_filesize_kb, compress_level)

        size_info = f"{original_size}"
        if original_size != new_size:
            size_info += f" → {new_size}"
        size_info += f", {file_kb}KB"

        if max_filesize_kb > 0 and file_kb > max_filesize_kb:
            return True, f"⚠️  {out_path.name} ({size_info}) — {max_filesize_kb}KB以下に収まりませんでした"
        else:
            return True, f"✅ {out_path.name} ({size_info})"

    except Exception as e:
        return False, f"❌ {heic_path.name}: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="HEICファイルをまとめてPNGに変換するツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python heic_to_png.py                           # カレントディレクトリの全HEIC
  python heic_to_png.py ~/Pictures                 # 指定ディレクトリ
  python heic_to_png.py photo1.heic photo2.HEIC    # 個別ファイル
  python heic_to_png.py -o output/ ~/Pictures      # 出力先を指定
  python heic_to_png.py --width 1920               # 長辺1920pxにリサイズ
  python heic_to_png.py --scale 50                 # 50%に縮小
  python heic_to_png.py --max-filesize 500         # 500KB以下に収める
  python heic_to_png.py -r ~/Pictures              # サブディレクトリも再帰的に

環境変数:
  HEIC_PNG_WIDTH       デフォルトの長辺px (0=リサイズなし)
  HEIC_PNG_SCALE       デフォルトのスケール% (0=スケールなし)
  HEIC_PNG_MAX_KB      デフォルトの最大ファイルサイズKB (0=制限なし)
  HEIC_PNG_QUALITY     PNG圧縮レベル 0-9 (デフォルト: 9)
        """
    )
    parser.add_argument("paths", nargs="*", default=["."],
                        help="変換するHEICファイルまたはディレクトリ (デフォルト: カレントディレクトリ)")
    parser.add_argument("-o", "--output", default=None,
                        help="出力先ディレクトリ (デフォルト: 元ファイルと同じ場所)")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH,
                        help=f"長辺を指定pxにリサイズ (デフォルト: {DEFAULT_WIDTH or 'リサイズなし'})")
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE,
                        help=f"指定パーセントに縮小 (デフォルト: {DEFAULT_SCALE or 'スケールなし'})")
    parser.add_argument("--max-filesize", type=int, default=DEFAULT_MAX_FILESIZE,
                        help=f"最大ファイルサイズKB。超える場合は段階的に縮小 (デフォルト: {DEFAULT_MAX_FILESIZE or '制限なし'})")
    parser.add_argument("--compress", type=int, default=DEFAULT_QUALITY,
                        choices=range(0, 10),
                        help=f"PNG圧縮レベル 0-9 (デフォルト: {DEFAULT_QUALITY}、9が最高圧縮)")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="サブディレクトリも再帰的に検索")
    parser.add_argument("--dry-run", action="store_true",
                        help="変換せず対象ファイルの一覧を表示")
    args = parser.parse_args()

    # --width と --scale は同時指定不可
    if args.width > 0 and args.scale > 0:
        print("[ERROR] --width と --scale は同時に指定できません", file=sys.stderr)
        sys.exit(1)

    # HEICファイルを収集
    heic_files = collect_heic_files(args.paths, args.recursive)
    if not heic_files:
        print("変換対象のHEICファイルが見つかりませんでした")
        sys.exit(0)

    print(f"\n🔍 {len(heic_files)}個のHEICファイルを検出")

    # リサイズ情報
    resize_info = []
    if args.width > 0:
        resize_info.append(f"長辺{args.width}px")
    if args.scale > 0:
        resize_info.append(f"{args.scale}%に縮小")
    if args.max_filesize > 0:
        resize_info.append(f"最大{args.max_filesize}KB")
    if resize_info:
        print(f"  サイズ調整: {', '.join(resize_info)}")

    # dry-run
    if args.dry_run:
        print("\n[dry-run] 以下のファイルが変換対象です:")
        for f in heic_files:
            try:
                img = Image.open(f)
                fsize = f.stat().st_size // 1024
                print(f"  {f} ({img.width}x{img.height}, {fsize}KB)")
            except Exception:
                print(f"  {f} (読み取りエラー)")
        sys.exit(0)

    # 出力ディレクトリ
    output_dir = None
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"  出力先: {output_dir.resolve()}")

    # 変換実行
    print()
    t_start = time.time()
    success_count = 0
    fail_count = 0

    for i, heic_file in enumerate(heic_files, 1):
        print(f"[{i}/{len(heic_files)}] {heic_file.name} ... ", end="", flush=True)
        ok, msg = convert_heic_to_png(
            heic_file, output_dir,
            args.width, args.scale, args.max_filesize, args.compress,
        )
        print(msg)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    elapsed = time.time() - t_start
    print(f"\n{'─' * 40}")
    print(f"完了: {success_count}個変換", end="")
    if fail_count:
        print(f", {fail_count}個失敗", end="")
    print(f" ({elapsed:.1f}秒)")


if __name__ == "__main__":
    main()
