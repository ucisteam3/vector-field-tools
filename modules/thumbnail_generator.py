"""
Thumbnail Generator Module
Auto-creates vertical (9:16) thumbnails for exported clips.
Supports person detection from transcript, image search, and dramatic sports-style design.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Tuple

# Optional: image search (don't fail if missing)
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Output size: vertical 9:16 (YouTube Shorts style)
THUMB_WIDTH = 1080
THUMB_HEIGHT = 1920

# Person image search query suffix
PERSON_SEARCH_SUFFIX = " portrait football coach"


def extract_person_name(transcript_text: str) -> Optional[str]:
    """
    Detect a known person name from clip transcript using simple rules.
    Examples: "Bojan Hodak mengatakan..." -> "Bojan Hodak"
    """
    if not transcript_text or not isinstance(transcript_text, str):
        return None
    text = transcript_text.strip()
    if not text:
        return None

    # Pattern: "Name Name ..." followed by verb ( mengatakan, menyatakan, mengungkapkan, etc.)
    verb_pattern = r"\s+(?:menyatakan|mengungkapkan|mengatakan|bilang|ujar|ungkap)\b"
    match = re.search(r"([A-Z][a-zA-Z\u00C0-\u024F]+(?:\s+[A-Z][a-zA-Z\u00C0-\u024F]+){0,3})" + verb_pattern, text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Reject single-word "names" that are common words
        if len(name) > 2 and name.lower() not in ("the", "and", "atau", "dan", "ini", "itu"):
            return name

    # Single-word name before verb/predicate (e.g. "Kurzawa perlu tingkatkan", "Beckham akan")
    single_verb = re.search(
        r"\b([A-Z][a-z\u00C0-\u024F]{3,})\s+(?:perlu|akan|harus|masih|sudah|pernah|ingin|bisa)\b",
        text, re.IGNORECASE
    )
    if single_verb:
        name = single_verb.group(1).strip()
        if name.lower() not in ("the", "and", "atau", "dan", "ini", "itu", "apa", "siapa"):
            return name
    # Fallback: first sequence of 2+ capitalized words (likely a name)
    cap_seq = re.findall(r"\b([A-Z][a-z\u00C0-\u024F]+(?:\s+[A-Z][a-z\u00C0-\u024F]+)+)\b", text)
    if cap_seq:
        candidate = cap_seq[0].strip()
        if len(candidate) >= 4 and len(candidate.split()) >= 2:
            return candidate
    return None


def search_and_download_person_image(person_name: str, temp_dir: Path) -> Optional[Path]:
    """
    Search for a real image of the person and download the first usable result.
    Tries DuckDuckGo with query including suffix, then name only. Uses User-Agent to avoid 403.
    """
    if not DDGS_AVAILABLE or not person_name:
        return None
    import urllib.request
    # User-Agent so some image hosts don't block
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")]
    urllib.request.install_opener(opener)
    queries = [f'"{person_name}"{PERSON_SEARCH_SUFFIX}', f'"{person_name}" football', person_name]
    for query in queries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=8))
            if not results:
                continue
            for r in results[:6]:
                url = r.get("image")
                if not url or not isinstance(url, str):
                    continue
                try:
                    ext = ".jpg" if "jpg" in url.lower() else ".png"
                    out_path = temp_dir / f"person_{abs(hash(person_name)) % 100000}{ext}"
                    urllib.request.urlretrieve(url, str(out_path))
                    if out_path.exists() and out_path.stat().st_size > 2000:
                        return out_path
                except Exception:
                    continue
        except Exception as e:
            logging.getLogger(__name__).debug("Thumbnail image search %s: %s", query[:30], e)
    return None


def _crop_center_face_region(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop center of image (simple center crop for face/subject)."""
    w, h = img.size
    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def create_fallback_background() -> Image.Image:
    """
    Generate a generic dramatic football/sports themed background (9:16).
    Dark gradient with subtle spotlight effect, no external API.
    """
    img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), (10, 15, 20))
    draw = ImageDraw.Draw(img)
    # Vertical gradient: darker at top, slightly lighter at center (spotlight)
    for y in range(THUMB_HEIGHT):
        t = y / THUMB_HEIGHT
        r = int(10 + 25 * (1 - abs(t - 0.4)))
        g = int(18 + 35 * (1 - abs(t - 0.4)))
        b = int(25 + 30 * (1 - abs(t - 0.4)))
        draw.line([(0, y), (THUMB_WIDTH, y)], fill=(r, g, b))
    # Light vignette (coarse grid for speed)
    for x in range(0, THUMB_WIDTH, 24):
        for y in range(0, THUMB_HEIGHT, 24):
            dx = (x / THUMB_WIDTH - 0.5) * 2
            dy = (y / THUMB_HEIGHT - 0.5) * 2
            d = (dx * dx + dy * dy) ** 0.5
            if d > 0.5:
                try:
                    current = img.getpixel((x, y))
                    darken = max(0, int(60 * (d - 0.5)))
                    img.putpixel((x, y), (
                        max(0, current[0] - darken),
                        max(0, current[1] - darken),
                        max(0, current[2] - darken)
                    ))
                except Exception:
                    pass
    return img


def _get_thumbnail_font(font_size: int) -> ImageFont.FreeTypeFont:
    """Load bold, thumbnail-style font for hook text (YouTube Shorts / viral style)."""
    font_dir = Path("assets") / "fonts"
    # Prefer bold headline fonts: Bebas Neue, Archivo Black, Anton, Oswald, then Poppins/Roboto
    candidates = [
        "BebasNeue-Regular.ttf",
        "ArchivoBlack-Regular.ttf",
        "Anton-Regular.ttf",
        "Oswald-Bold.ttf",
        "LuckiestGuy-Regular.ttf",
        "Poppins-ExtraBold.ttf",
        "Poppins-Bold.ttf",
        "Montserrat-ExtraBold.ttf",
        "Roboto-Bold.ttf",
    ]
    for name in candidates:
        p = font_dir / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), font_size)
            except Exception:
                continue
    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        return ImageFont.load_default()


def _draw_hook_text(draw: ImageDraw.Draw, hook_text: str, font: ImageFont.FreeTypeFont,
                    width: int, height: int, outline_px: int = 6) -> None:
    """
    Draw hook text at bottom: bold, large, high contrast (thumbnail style).
    White/yellow text with thick black outline for readability.
    """
    if not hook_text:
        return
    # Wrap: ~22 chars per line for 1080px so font stays large
    words = hook_text.split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(" ".join(current)) > 22:
            lines.append(" ".join(current[:-1]))
            current = [w]
    if current:
        lines.append(" ".join(current))
    lines = lines[:3]
    text_block = "\n".join(lines)
    y_bottom = height - 200
    try:
        bbox = draw.textbbox((0, 0), text_block, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        try:
            tw, th = draw.textsize(text_block, font=font)
        except AttributeError:
            tw, th = 400, 90 * len(lines)
    x = (width - tw) // 2
    y = y_bottom - th
    # Thick black outline (thumbnail-style stroke)
    for dx in range(-outline_px, outline_px + 1):
        for dy in range(-outline_px, outline_px + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text_block, font=font, fill=(0, 0, 0))
    # Main text: bright white, slight warm tint
    draw.text((x, y), text_block, font=font, fill=(255, 255, 240))


def _generate_background_with_dalle(openai_client, hook_text: str, transcript_snippet: str, temp_dir: Path):
    """
    Generate thumbnail background image using OpenAI DALL-E 3. Returns PIL Image (RGB) or None.
    Size 1024x1792 (portrait); we resize to THUMB_WIDTH x THUMB_HEIGHT.
    """
    if not openai_client or not PIL_AVAILABLE:
        return None
    try:
        # Prompt for background only (no text - we overlay text ourselves for accuracy)
        context = (transcript_snippet or "")[:200].strip() or (hook_text or "")[:100]
        prompt = (
            "Dramatic YouTube Shorts thumbnail background, vertical format, cinematic lighting, "
            "sports news or viral content style, intense mood, professional, no text, no words, no letters. "
        )
        if context:
            prompt += f"Theme or mood inspired by: {context}. "
        prompt += "High quality, 9:16 aspect ratio, suitable for headline overlay at bottom."
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792",
            quality="standard",
            n=1,
        )
        url = getattr(response.data[0], "url", None) if response.data else None
        if not url:
            return None
        import urllib.request
        out_path = temp_dir / f"dalle_{hash(prompt) % 100000}.png"
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, str(out_path))
        if not out_path.exists() or out_path.stat().st_size < 1000:
            return None
        img = Image.open(out_path).convert("RGB")
        img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        logging.getLogger(__name__).debug("DALL-E thumbnail background failed: %s", e)
        return None


def generate_thumbnail(
    clip_path: str,
    transcript_text: str,
    hook_text: str,
    output_path: str,
    openai_client=None,
    use_ai_background: bool = False,
) -> bool:
    """
    Generate a vertical (9:16) thumbnail for the clip.
    - If use_ai_background and openai_client: try DALL-E 3 for background.
    - Else if person name in transcript: try DuckDuckGo photo.
    - Else: gradient fallback.
    Hook text is drawn at bottom with bold font.
    Returns True on success, False on failure (caller should not block export).
    """
    if not PIL_AVAILABLE:
        logging.getLogger(__name__).warning("PIL not available; thumbnail skipped")
        return False

    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path("temp") / "thumbnails"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 1) Background: DALL-E, then person image, then fallback gradient
        bg_image = None
        if use_ai_background and openai_client:
            bg_image = _generate_background_with_dalle(
                openai_client, hook_text or "", (transcript_text or "")[:500], temp_dir
            )
        if bg_image is None:
            person_name = extract_person_name(transcript_text or "")
            if person_name:
                person_img_path = search_and_download_person_image(person_name, temp_dir)
                if person_img_path and person_img_path.exists():
                    try:
                        bg_image = Image.open(person_img_path).convert("RGB")
                        bg_image = _crop_center_face_region(bg_image, THUMB_WIDTH, THUMB_HEIGHT)
                    except Exception:
                        bg_image = None
        if bg_image is None:
            bg_image = create_fallback_background()

        # 2) Optional dark overlay for text readability
        overlay = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(0, THUMB_HEIGHT - 400), (THUMB_WIDTH, THUMB_HEIGHT)], fill=(0, 0, 0, 140))
        bg_image = bg_image.convert("RGBA")
        bg_image = Image.alpha_composite(bg_image, overlay)
        bg_image = bg_image.convert("RGB")
        draw = ImageDraw.Draw(bg_image)

        # 3) Hook text at bottom (large, thumbnail-style font)
        hook_str = (hook_text or "").strip() or "Clip"
        # Font size: base ~78pt, minimum 58, so text stays big and readable
        font_size = max(58, min(100, 82 - len(hook_str) // 3))
        font = _get_thumbnail_font(font_size)
        _draw_hook_text(draw, hook_str, font, THUMB_WIDTH, THUMB_HEIGHT, outline_px=7)

        # 4) Save
        bg_image.save(str(output_path), "PNG", quality=95)
        return True
    except Exception as e:
        logging.getLogger(__name__).exception("Thumbnail generation failed: %s", e)
        return False
