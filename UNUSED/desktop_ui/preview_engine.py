import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageColor
try:
    from PIL import ImageTk
    import tkinter as tk
    _tk_pil_available = True
except ImportError:
    ImageTk = None
    tk = None
    _tk_pil_available = False

def draw_mobile_ui(draw, w, h, scale):
    """Draw procedural Mobile App UI Overlay (Shorts styling)"""
    # Colors
    ICON_COLOR = "#FFFFFF"
    TEXT_COLOR = "#FFFFFF"
    ACCENT_COLOR = "#FF0000" # Red
    
    # Fonts (Simple fallback sizing)
    # Scale reference: scale=1.0 for 1080p. UI usually small.
    # On 270x480 preview, scale=0.25.
    
    def get_font(size_pt):
        try:
            return ImageFont.truetype("arial.ttf", int(size_pt * scale * 2)) 
        except:
            return ImageFont.load_default()

    font_icon = get_font(24) # ~12px on preview
    font_sm = get_font(14)
    font_bold = get_font(16)
    
    # 1. TOP BAR
    # Back Arrow (Left), Search (Right)
    # Simple shapes/text proxies
    margin = int(20 * scale)
    top_y = int(40 * scale)
    
    # Back ( < )
    draw.text((margin, top_y), "<", font=font_icon, fill=ICON_COLOR)
    # Search ( O- )
    search_x = w - margin - int(30 * scale)
    draw.ellipse((search_x, top_y, search_x + int(20*scale), top_y + int(20*scale)), outline=ICON_COLOR, width=2)
    
    # 2. RIGHT SIDEBAR (Action Bar)
    # Fixed width on right
    right_x = w - int(60 * scale) # Center of icons
    start_y = h // 2 # Start from middle
    spacing = int(80 * scale)
    
    actions = ["Like", "1.2M", "Dislike", "Dislike", "Comment", "4k", "Share", "Share", "Remix", "Remix"]
    # We will draw icons as circles + text below
    
    curr_y = start_y
    for i in range(0, len(actions), 2):
        icon_name = actions[i]
        label = actions[i+1] if i+1 < len(actions) else ""
        
        # Icon Circle
        r = int(20 * scale)
        cx = right_x
        cy = curr_y
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=ICON_COLOR, width=2)
        
        # Label
        if label:
            # Center text
            # draw.textbbox not available in older PIL? Assume it is from context.
            bb = draw.textbbox((0,0), label, font=font_sm)
            tw = bb[2] - bb[0]
            draw.text((cx - tw//2, cy + r + 2), label, font=font_sm, fill=TEXT_COLOR)
            
        curr_y += spacing

    # 3. BOTTOM INFO AREA
    # User, Subscribe, Desc
    # Stacked from bottom up (above nav bar)
    
    # Nav Bar Height approx 150px on 1080p -> 150 * 0.25 = 37px
    nav_h = int(140 * scale)
    info_bottom = h - nav_h - int(20 * scale)
    
    # Description (2 lines)
    desc_start_x = int(20 * scale)
    desc_y = info_bottom
    draw.text((desc_start_x, desc_y), "#fyp #viral #shorts", font=font_sm, fill=TEXT_COLOR)
    draw.text((desc_start_x, desc_y - int(25*scale)), "Video description text goes here...", font=font_sm, fill=TEXT_COLOR)
    
    # Username + Subscribe
    user_y = desc_y - int(60 * scale)
    draw.text((desc_start_x, user_y), "@username", font=font_bold, fill=TEXT_COLOR)
    
    # Subscribe setup
    # Measure username to place button
    bb_u = draw.textbbox((0,0), "@username", font=font_bold)
    u_w = bb_u[2] - bb_u[0]
    
    btn_x = desc_start_x + u_w + int(15 * scale)
    
    # Measure "Subscribe" text to fit button
    sub_text = "Subscribe"
    bb_s = draw.textbbox((0,0), sub_text, font=font_sm)
    s_w = bb_s[2] - bb_s[0]
    
    btn_w = s_w + int(20 * scale) # Padding
    btn_h = int(30 * scale)
    
    # Red Button
    draw.rectangle((btn_x, user_y, btn_x + btn_w, user_y + btn_h), fill=ACCENT_COLOR)
    draw.text((btn_x + int(10*scale), user_y + int(2*scale)), sub_text, font=font_sm, fill="white")
    
    # 4. BOTTOM NAV BAR
    # Home, Shorts, (+), Subs, Profile
    nav_y = h - nav_h + int(20*scale)
    nav_items = ["Home", "Shorts", "+", "Subs", "You"]
    
    section_w = w / 5
    for i, item in enumerate(nav_items):
        cx = int(section_w * i + section_w/2)
        cy = nav_y
        
        if item == "+":
            # Big Circle
            r = int(25 * scale)
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=ICON_COLOR, width=2)
        else:
            # Small icon box
            r = int(12 * scale)
            draw.rectangle((cx-r, cy-r, cx+r, cy+r), outline=ICON_COLOR)
            
        draw.text((cx - int(10*scale), cy + int(20*scale)), item, font=font_sm, fill=TEXT_COLOR)

def render_subtitle_preview(canvas, settings, font_dir=None):
    """
    Render subtitle preview on the given canvas using PIL for high quality text.
    """
    if not canvas or not canvas.winfo_exists():
        return

    # Canvas dimensions
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    
    # Avoid rendering on zero size (startup)
    if width <= 1 or height <= 1:
        # Default fallback if canvas not ready
        width, height = 270, 480 

    # Get Project Root (modules/../)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    assets_dir = os.path.join(project_root, "assets")
    
    # 1. Create Preview Background with layout-baru.png
    sample_image_path = os.path.join(assets_dir, "img", "layout-baru.png")
    
    if os.path.exists(sample_image_path):
        try:
            # Load sample image
            image = Image.open(sample_image_path).convert('RGB')
            
            # Scale to cover canvas
            img_w, img_h = image.size
            canvas_ratio = width / height
            img_ratio = img_w / img_h
            
            if img_ratio > canvas_ratio:
                scale_factor = height / img_h
            else:
                scale_factor = width / img_w
            
            # Add 5% zoom
            scale_factor *= 1.05
            
            new_width = int(img_w * scale_factor)
            new_height = int(img_h * scale_factor)
            
            # Resize
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            right = left + width
            bottom = top + height
            image = image.crop((left, top, right, bottom))
            
        except Exception as e:
            print(f"[PREVIEW] Could not load layout-baru.png: {e}, using black")
            image = Image.new('RGB', (width, height), (0, 0, 0))
    else:
        # Fallback to black if not found
        image = Image.new('RGB', (width, height), (0, 0, 0))
    
    # Redraw for text overlay
    draw = ImageDraw.Draw(image)

    # 3. Extract Settings
    text = "Contoh Subtitle Viral\nKata Demi Kata"
    font_name = settings.get("subtitle_font", "Arial")
    base_fontsize = settings.get("subtitle_fontsize", 24)
    primary_color = settings.get("subtitle_text_color", "#FFFFFF")

    outline_color = settings.get("subtitle_outline_color", "#000000")
    highlight_color = settings.get("subtitle_highlight_color", "#FFFF00")
    
    # print(f"[PREVIEW] Rendering: Primary={primary_color} Outline={outline_color} Highlight={highlight_color}") # Quiet
    
    outline_width_setting = settings.get("subtitle_outline_width", 2)
    pos_y_setting = settings.get("subtitle_position_y", 50) # From bottom
    
    # Scale factors (UI Canvas is smaller than actual 1080x1920 video)
    # [ROBUST] Handle winfo_width() being 1 on first load
    canvas_w = width if width > 10 else 270
    canvas_h = height if height > 10 else 480
    
    scale = canvas_w / 1080.0
    
    # Adjusted font size for preview
    # [CRITICAL FIX] The 10x multiplier is for EXPORT at 1920p resolution
    # Preview should use base_fontsize directly, scaled to canvas size
    # Export: base * 10 for 1920p (e.g., 24 * 10 = 240pt)
    # Preview: base * (canvas_h / reference_height) where reference ~= 480-600px
    # Since canvas is ~480px and we want similar visual size, use base directly with small scale
    # Adjusted to 1.1x to avoid being too large in preview, while keeping export at 6x
    preview_fontsize = int(base_fontsize * (canvas_h / 480.0) * 1.1)
    if preview_fontsize < 6: preview_fontsize = 6
    
    # Load Font
    font_path = None
    if font_dir:
        # Try finding the font in assets
        possible_names = [f"{font_name}.ttf", f"{font_name}.otf", f"{font_name}-Bold.ttf", f"{font_name}-Regular.ttf"]
        for fname in possible_names:
            fpath = os.path.join(font_dir, fname)
            if os.path.exists(fpath):
                font_path = fpath
                break
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, size=preview_fontsize)
        else:
            # System font fallback
            font = ImageFont.truetype("arial.ttf", size=preview_fontsize)
    except:
        font = ImageFont.load_default()

    # 3. Calculate Position
    # [UNIFY] Use 1:1 pixel mapping for margin from bottom (matching Export/Watermark)
    margin_bottom = int(pos_y_setting * (canvas_h / 1920.0))
    
    # Render sample text with specific word highlighting
    # Text: "Contoh Subtitle Viral"
    # Highlight: "Subtitle"
    
    parts = [("Contoh ", primary_color), ("Subtitle ", highlight_color), ("Viral ", primary_color), ("Gini", primary_color)]
    
    # Calculate widths first to center
    total_w = 0
    max_h = 0
    part_sizes = []
    # Define stroke width - scale from 1920p base
    # Export uses outline_width_setting directly at 1920p
    stroke_width = int(outline_width_setting * (canvas_h / 1920.0))
    if stroke_width < 1: stroke_width = 1

    for text_part, color in parts:
        bbox = draw.textbbox((0, 0), text_part, font=font, stroke_width=stroke_width)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        part_sizes.append((w, h, text_part, color))
        total_w += w
        max_h = max(max_h, h)
        
    start_x = (canvas_w - total_w) // 2

    # Second line "Kata Demi Kata Saja"
    line2 = "Kata Demi Kata Saja"
    bbox2 = draw.textbbox((0, 0), line2, font=font, stroke_width=stroke_width)
    w2 = bbox2[2] - bbox2[0]
    h2 = bbox2[3] - bbox2[1]
    
    # [FIX] Tighter Spacing for better Parity with FFmpeg/libass
    spacing = int(5 * scale * 4) # Scale 4 at 1080p -> 1 at 480p? Let's use simpler
    spacing = int(20 * scale) # approx 5px on preview
    
    total_block_h = max_h + spacing + h2
    
    # draw_y is the TOP of the first line. 
    # To match FFmpeg Alignment 2, the BOTTOM of the last line must sit at (height - margin_bottom)
    draw_y = canvas_h - margin_bottom - total_block_h

    current_x = start_x
    for w, h, text_part, color in part_sizes:
        draw.text((current_x, draw_y), text_part, font=font, fill=color, 
                  stroke_width=stroke_width, stroke_fill=outline_color)
        current_x += w
    
    x2 = (canvas_w - w2) // 2
    draw.text((x2, draw_y + max_h + spacing), line2, font=font, fill=primary_color,
              stroke_width=stroke_width, stroke_fill=outline_color)

    # === WATERMARK RENDERING ===
    if settings.get("watermark_enabled", False):
        try:
            wm_type = settings.get("watermark_type", "text")
            # Calculate Position
            # X = Percentage (0-100)
            # Y = Bottom Margin (0-500px)
            pos_x_pct = settings.get("watermark_pos_x", 50)
            pos_y_margin = settings.get("watermark_pos_y", 50) # px from bottom
            
            # Preview Scale Logic
            # Preview Height ~480 vs Video 1920 (Scale ~0.25)
            # margin_px_preview = pos_y_margin * (height / 1920.0) * 4 # Approximate scaling
            # Simplified: scale factor is 'scale' variable (approx 0.25)
            # But 'scale' is derived from width.
             
            wm_x = int(width * (pos_x_pct / 100.0))
            # Y = Height - Scaled Margin
            # We treat pos_y_margin as 1080p-equivalent pixels.
            wm_y = int(height - (pos_y_margin * scale))
            
            if wm_type == "text":
                wm_text = settings.get("watermark_text", "Watermark")
                if wm_text:
                    wm_size_base = settings.get("watermark_size", 48)
                    wm_op = settings.get("watermark_opacity", 80) / 100.0
                    wm_col_hex = settings.get("watermark_color", "#FFFFFF")
                    wm_out_hex = settings.get("watermark_outline_color", "#000000")
                    wm_out_width = settings.get("watermark_outline_width", 2)
                    
                    # Convert to RGBA
                    wm_rgb = ImageColor.getrgb(wm_col_hex)
                    wm_rgba = (wm_rgb[0], wm_rgb[1], wm_rgb[2], int(255 * wm_op))
                    wm_out_rgb = ImageColor.getrgb(wm_out_hex)
                    wm_out_rgba = (wm_out_rgb[0], wm_out_rgb[1], wm_out_rgb[2], int(255 * wm_op)) # Same opacity
                    
                    # Font (Try to load user font)
                    wm_font_name = settings.get("watermark_font", "Arial")
                    # [FIX] Match Subtitle Scaling logic (10x scale for preview)
                    wm_font_sz = int(wm_size_base * scale * 10)
                    try:
                        wm_font = ImageFont.truetype("arial.ttf", size=wm_font_sz)
                    except:
                        wm_font = ImageFont.load_default()

                    if font_dir:
                        possibles = [f"{wm_font_name}.ttf", f"{wm_font_name}.otf", f"{wm_font_name}-Bold.ttf", f"{wm_font_name}-Regular.ttf"]
                        for f in possibles:
                            if os.path.exists(os.path.join(font_dir, f)):
                                wm_font = ImageFont.truetype(os.path.join(font_dir, f), size=wm_font_sz)
                                break
                    
                    # Center text on anchor
                    bbox = draw.textbbox((0,0), wm_text, font=wm_font, stroke_width=wm_out_width)
                    w_w = bbox[2] - bbox[0]
                    w_h = bbox[3] - bbox[1]
                    draw_x = wm_x - w_w // 2
                    # [FIX] Align with FFmpeg H-text_h-margin (Bottom Anchor)
                    draw_y_wm = wm_y - w_h
                    
                    # Draw on Overlay Layer
                    wm_layer = Image.new('RGBA', (width, height), (0,0,0,0))
                    wm_draw = ImageDraw.Draw(wm_layer)
                    wm_draw.text((draw_x, draw_y_wm), wm_text, font=wm_font, fill=wm_rgba, 
                               stroke_width=wm_out_width, stroke_fill=wm_out_rgba)
                    
                    # Composite (convert to RGBA for compositing, then back to RGB)
                    image = Image.alpha_composite(image.convert('RGBA'), wm_layer).convert('RGB')
                    draw = ImageDraw.Draw(image) # Restore draw
                    
            elif wm_type == "image":
                wm_path = settings.get("watermark_image_path", "")
                if wm_path and os.path.exists(wm_path):
                    wm_img = Image.open(wm_path).convert("RGBA")
                    # [FIX] Match Export Image Scaling (iw * scale_pct)
                    user_scale = settings.get("watermark_image_scale", 50) / 100.0
                    target_w = int(wm_img.width * user_scale * scale)
                    if target_w < 10: target_w = 10
                    aspect = wm_img.height / wm_img.width
                    target_h = int(target_w * aspect)
                    
                    wm_img = wm_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    # Opacity
                    wm_op = settings.get("watermark_image_opacity", 100) / 100.0
                    if wm_op < 1.0:
                        alpha = wm_img.split()[3]
                        alpha = ImageEnhance.Brightness(alpha).enhance(wm_op)
                        wm_img.putalpha(alpha)
                    
                    # [FIX] Match Export Overlay (Bottom Anchor)
                    paste_x = wm_x - target_w // 2
                    paste_y = wm_y - target_h
                    
                    image.paste(wm_img, (paste_x, paste_y), wm_img)
                    
        except Exception as e:
            print(f"[PREVIEW ERROR] Watermark render failed: {e}")

    # === OVERLAY RENDERING (Second Watermark) ===
    if settings.get("overlay_enabled", False):
        try:
            ov_type = settings.get("overlay_type", "text")
            # Calculate Position
            pos_x_pct = settings.get("overlay_pos_x", 50)
            pos_y_margin = settings.get("overlay_pos_y", 200)
            
            ov_x = int(width * (pos_x_pct / 100.0))
            ov_y = int(height - (pos_y_margin * scale))
            
            if ov_type == "text":
                ov_text = settings.get("overlay_text", "Overlay")
                if ov_text:
                    ov_size_base = settings.get("overlay_size", 48)
                    ov_op = settings.get("overlay_opacity", 80) / 100.0
                    ov_col_hex = settings.get("overlay_color", "#FFFFFF")
                    ov_out_hex = settings.get("overlay_outline_color", "#000000")
                    ov_out_width = settings.get("overlay_outline_width", 2)
                    
                    # Convert to RGBA
                    ov_rgb = ImageColor.getrgb(ov_col_hex)
                    ov_rgba = (ov_rgb[0], ov_rgb[1], ov_rgb[2], int(255 * ov_op))
                    ov_out_rgb = ImageColor.getrgb(ov_out_hex)
                    ov_out_rgba = (ov_out_rgb[0], ov_out_rgb[1], ov_out_rgb[2], int(255 * ov_op))
                    
                    # Font
                    ov_font_name = settings.get("overlay_font", "Arial")
                    ov_font_sz = int(ov_size_base * scale * 10)
                    try:
                        ov_font = ImageFont.truetype("arial.ttf", size=ov_font_sz)
                    except:
                        ov_font = ImageFont.load_default()

                    if font_dir:
                        possibles = [f"{ov_font_name}.ttf", f"{ov_font_name}.otf", f"{ov_font_name}-Bold.ttf", f"{ov_font_name}-Regular.ttf"]
                        for f in possibles:
                            if os.path.exists(os.path.join(font_dir, f)):
                                ov_font = ImageFont.truetype(os.path.join(font_dir, f), size=ov_font_sz)
                                break
                    
                    # Center text on anchor
                    bbox = draw.textbbox((0,0), ov_text, font=ov_font, stroke_width=ov_out_width)
                    o_w = bbox[2] - bbox[0]
                    o_h = bbox[3] - bbox[1]
                    draw_x = ov_x - o_w // 2
                    draw_y_ov = ov_y - o_h
                    
                    # Draw on Overlay Layer
                    ov_layer = Image.new('RGBA', (width, height), (0,0,0,0))
                    ov_draw = ImageDraw.Draw(ov_layer)
                    ov_draw.text((draw_x, draw_y_ov), ov_text, font=ov_font, fill=ov_rgba, 
                               stroke_width=ov_out_width, stroke_fill=ov_out_rgba)
                    
                    # Composite
                    image = Image.alpha_composite(image.convert('RGBA'), ov_layer).convert('RGB')
                    draw = ImageDraw.Draw(image)
                    
            elif ov_type == "image":
                ov_path = settings.get("overlay_image_path", "")
                if ov_path and os.path.exists(ov_path):
                    ov_img = Image.open(ov_path).convert("RGBA")
                    user_scale = settings.get("overlay_image_scale", 50) / 100.0
                    target_w = int(ov_img.width * user_scale * scale)
                    if target_w < 10: target_w = 10
                    aspect = ov_img.height / ov_img.width
                    target_h = int(target_w * aspect)
                    
                    ov_img = ov_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    # Opacity
                    ov_op = settings.get("overlay_image_opacity", 100) / 100.0
                    if ov_op < 1.0:
                        alpha = ov_img.split()[3]
                        alpha = ImageEnhance.Brightness(alpha).enhance(ov_op)
                        ov_img.putalpha(alpha)
                    
                    # Bottom Anchor
                    paste_x = ov_x - target_w // 2
                    paste_y = ov_y - target_h
                    
                    image.paste(ov_img, (paste_x, paste_y), ov_img)
                    
        except Exception as e:
            print(f"[PREVIEW ERROR] Overlay render failed: {e}")

    # === SOURCE CREDIT RENDERING ===
    if settings.get("source_credit_enabled", False):
        try:
            # Default text jika metadata belum ada (misalnya belum fetch dari YouTube)
            credit_text = "Source: Sample Channel"
            
            # Coba akses parent utama (YouTubeHeatmapAnalyzer) dari canvas
            try:
                parent = None
                if hasattr(canvas, 'master') and hasattr(canvas.master, 'master'):
                    parent = canvas.master.master

                # Prioritas 1: gunakan metadata channel_name dari main.py
                if parent is not None and hasattr(parent, "channel_name"):
                    channel_name = getattr(parent, "channel_name", None)
                    if channel_name and channel_name != "Unknown Channel":
                        credit_text = f"Source: {channel_name}"
                # Prioritas 2: fallback ke label UI jika ada
                if parent is not None and credit_text == "Source: Sample Channel":
                    try:
                        if hasattr(parent, "channel_name_label"):
                            ui_channel = parent.channel_name_label.cget("text")
                            if ui_channel and ui_channel != "-":
                                credit_text = f"Source: {ui_channel}"
                    except Exception:
                        pass
                # Prioritas 3: terakhir, heuristik dari nama file (hanya jika ada pola " - ")
                if parent is not None and credit_text == "Source: Sample Channel":
                    if hasattr(parent, "video_path") and parent.video_path:
                        from pathlib import Path
                        video_path = Path(parent.video_path)
                        video_stem = video_path.stem
                        # Hanya gunakan jika ada separator " - " (pola: "Channel - Title")
                        if ' - ' in video_stem:
                            channel_name = video_stem.split(' - ')[0]
                            channel_name = channel_name.split('[')[0].strip()
                            if channel_name:
                                credit_text = f"Source: {channel_name}"
            except Exception:
                # Biarkan pakai default jika ada error
                pass
            
            if credit_text:
                # Font settings
                credit_font_name = settings.get("source_credit_font", "Arial")
                credit_size_base = settings.get("source_credit_fontsize", 24)
                credit_font_sz = int(credit_size_base * scale * 10)
                
                # Color and opacity
                credit_col_hex = settings.get("source_credit_color", "#FFFFFF")
                credit_op = settings.get("source_credit_opacity", 80) / 100.0
                
                # Convert to RGBA
                credit_rgb = ImageColor.getrgb(credit_col_hex)
                credit_rgba = (credit_rgb[0], credit_rgb[1], credit_rgb[2], int(255 * credit_op))
                
                # Load font
                # Load font robustly (Assets Only)
                from modules.font_manager import VIRAL_FONTS
                font_path = None
                
                # 1. Map from VIRAL_FONTS
                if credit_font_name in VIRAL_FONTS:
                    local_font = f"assets/fonts/{VIRAL_FONTS[credit_font_name][1]}"
                    if os.path.exists(local_font):
                        font_path = local_font

                # 2. Direct filename
                if not font_path:
                    cand = f"assets/fonts/{credit_font_name}.ttf"
                    if os.path.exists(cand):
                        font_path = cand
                
                # 3. Fallback
                if not font_path:
                     fallback = "assets/fonts/Roboto-Bold.ttf"
                     if os.path.exists(fallback):
                         font_path = fallback
                
                try:
                    if font_path:
                        credit_font = ImageFont.truetype(font_path, size=credit_font_sz)
                    else:
                        credit_font = ImageFont.load_default()
                except:
                    credit_font = ImageFont.load_default()
                
                # Get text size first
                bbox = draw.textbbox((0,0), credit_text, font=credit_font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                # Position based on preset and offsets
                position = settings.get("source_credit_position", "bottom-right")
                offset_x = settings.get("source_credit_pos_x", 50)
                offset_y = settings.get("source_credit_pos_y", 100)
                
                # Scale offsets for preview
                scaled_offset_x = int(offset_x * scale)
                scaled_offset_y = int(offset_y * scale)
                
                # Calculate position based on preset
                if position == "top-left":
                    credit_x = scaled_offset_x
                    credit_y = scaled_offset_y
                elif position == "top-right":
                    credit_x = width - text_w - scaled_offset_x
                    credit_y = scaled_offset_y
                elif position == "bottom-left":
                    credit_x = scaled_offset_x
                    credit_y = height - text_h - scaled_offset_y
                else:  # bottom-right (default)
                    credit_x = width - text_w - scaled_offset_x
                    credit_y = height - text_h - scaled_offset_y
                
                # Draw on overlay layer
                credit_layer = Image.new('RGBA', (width, height), (0,0,0,0))
                credit_draw = ImageDraw.Draw(credit_layer)
                credit_draw.text((credit_x, credit_y), credit_text, font=credit_font, fill=credit_rgba)
                
                # Composite
                image = Image.alpha_composite(image.convert('RGBA'), credit_layer).convert('RGB')
                draw = ImageDraw.Draw(image)
                
        except Exception as e:
            print(f"[PREVIEW ERROR] Source credit render failed: {e}")

    # Convert PhotoImage and display on canvas (skip when headless or no tk)
    if canvas is not None and _tk_pil_available and ImageTk is not None and tk is not None:
        try:
            photo = ImageTk.PhotoImage(image)
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.image = photo
        except Exception:
            pass
