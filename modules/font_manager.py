import os
import requests
import threading
import time

FONT_DIR = os.path.join("assets", "fonts")
INSTALLED_MARKER = os.path.join(FONT_DIR, ".installed")

# Direct links to TTF files (GitHub raw)
# Google Fonts structure varies. 
# Many viral fonts are now Variable fonts, or located in 'static' subfolder.
BASE_URL_OFL = "https://github.com/google/fonts/raw/main/ofl"
BASE_URL_APACHE = "https://github.com/google/fonts/raw/main/apache"

# Mapping: Font Name -> (Subfolder, Filename, LicenseType, FolderVariant)
# FolderVariant: "" (default root), "static" (in static folder), or "variable" (custom handling)
VIRAL_FONTS = {
    # Working
    "Poppins-Bold": ("poppins", "Poppins-Bold.ttf", "ofl", ""),
    "Poppins-ExtraBold": ("poppins", "Poppins-ExtraBold.ttf", "ofl", ""),
    "BebasNeue-Regular": ("bebasneue", "BebasNeue-Regular.ttf", "ofl", ""),
    "Anton-Regular": ("anton", "Anton-Regular.ttf", "ofl", ""),
    "ArchivoBlack-Regular": ("archivoblack", "ArchivoBlack-Regular.ttf", "ofl", ""),
    "LuckiestGuy-Regular": ("luckiestguy", "LuckiestGuy-Regular.ttf", "apache", ""),

    # Fixing Failed ones
    # Montserrat is variable. Static is in 'static' folder.
    "Montserrat-Bold": ("montserrat", "Montserrat-Bold.ttf", "ofl", "static"),
    "Montserrat-ExtraBold": ("montserrat", "Montserrat-ExtraBold.ttf", "ofl", "static"),
    
    # Inter is variable. Static in 'static'.
    "Inter-Bold": ("inter", "Inter-Bold.ttf", "ofl", "static"),
    
    # Roboto is Apache, typically in root or static. Roboto-Bold.ttf usually in root but maybe Capitalization?
    # Checked: Roboto-Bold.ttf exists in apache/roboto/static/ usually for newer versions.
    "Roboto-Bold": ("roboto", "Roboto-Bold.ttf", "apache", "static"),
    
    # Oswald is variable.
    "Oswald-Bold": ("oswald", "Oswald-Bold.ttf", "ofl", "static"),
    
    # DM Sans is variable.
    "DM Sans-Bold": ("dmsans", "DMSans-Bold.ttf", "ofl", "static"),
    
    # Playfair Display is variable.
    "PlayfairDisplay-Bold": ("playfairdisplay", "PlayfairDisplay-Bold.ttf", "ofl", "static"),
    
    # League Spartan is variable.
    "LeagueSpartan-Bold": ("leaguespartan", "LeagueSpartan-Bold.ttf", "ofl", "static"),
    
    # Rubik is variable.
    "Rubik-Bold": ("rubik", "Rubik-Bold.ttf", "ofl", "static"),
    
    # Urbanist is variable.
    "Urbanist-Bold": ("urbanist", "Urbanist-Bold.ttf", "ofl", "static"),
    
    # Manrope is variable.
    "Manrope-Bold": ("manrope", "Manrope-Bold.ttf", "ofl", "static"),
    
    # Sora is variable.
    "Sora-Bold": ("sora", "Sora-Bold.ttf", "ofl", "static"),
}

# Mapping: Filename (Key) -> Actual Font Family Name (for ASS/Libass)
# This is crucial because libass reads the internal name, not filename.
FONT_NAME_MAP = {
    "Poppins-Bold": "Poppins",
    "Poppins-ExtraBold": "Poppins",
    "BebasNeue-Regular": "Bebas Neue",
    "Anton-Regular": "Anton",
    "ArchivoBlack-Regular": "Archivo Black",
    "LuckiestGuy-Regular": "Luckiest Guy",
    "Montserrat-Bold": "Montserrat",
    "Montserrat-ExtraBold": "Montserrat",
    "Inter-Bold": "Inter",
    "Roboto-Bold": "Roboto",
    "Oswald-Bold": "Oswald",
    "DM Sans-Bold": "DM Sans",
    "PlayfairDisplay-Bold": "Playfair Display",
    "LeagueSpartan-Bold": "League Spartan",
    "Rubik-Bold": "Rubik",
    "Urbanist-Bold": "Urbanist", 
    "Manrope-Bold": "Manrope",
    "Sora-Bold": "Sora",
}

def download_file(url, filepath):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"[FONTS] Downloaded: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"[FONTS] Failed to download {url}: {e}")
        return False

def download_default_fonts():
    """Download fonts only if .installed marker doesn't exist"""
    if not os.path.exists(FONT_DIR):
        os.makedirs(FONT_DIR, exist_ok=True)
        
    if os.path.exists(INSTALLED_MARKER):
        # Already installed, skip
        print("[FONTS] Fonts already installed (cache detected).")
        return

    def _worker():
        print("[FONTS] Starting Viral Fonts Download...")
        success_count = 0
        total_count = len(VIRAL_FONTS)
        
        for name, (folder, filename, license_type, variant) in VIRAL_FONTS.items():
            base = BASE_URL_OFL if license_type == "ofl" else BASE_URL_APACHE
            
            # Construct URL based on variant
            if variant == "static":
                url = f"{base}/{folder}/static/{filename}"
            else:
                url = f"{base}/{folder}/{filename}"
                
            filepath = os.path.join(FONT_DIR, filename)
            
            if not os.path.exists(filepath):
                if download_file(url, filepath):
                    success_count += 1
                else:
                    # Fallback try: maybe it's in root if static failed?
                    if variant == "static":
                        print(f"       -> Retrying {filename} in root...")
                        fallback_url = f"{base}/{folder}/{filename}"
                        if download_file(fallback_url, filepath):
                            success_count += 1
            else:
                success_count += 1
                
        # Create marker file if at least some fonts exist
        if success_count > 0:
            with open(INSTALLED_MARKER, "w", encoding="utf-8") as f:
                f.write(f"Installed on {time.ctime()}")
            print(f"[FONTS] Download complete. {success_count}/{total_count} fonts ready.")
        else:
            print("[FONTS] Download failed. No fonts obtained.")
        
    threading.Thread(target=_worker, daemon=True).start()

def load_fonts_from_folder():
    """Return list of font names available in assets/fonts"""
    fonts = []
    
    if os.path.exists(FONT_DIR):
        for f in os.listdir(FONT_DIR):
            if f.lower().endswith((".ttf", ".otf")):
                # Show full filename as font name (easier for user to distiguish Bold/ExtraBold)
                # Or strip extension
                font_name = os.path.splitext(f)[0]
                fonts.append(font_name)
    
    # Sort alphabetically
    fonts.sort()
    
    # If folder empty, provide fallback
    if not fonts:
        fonts = ["Arial", "Verdana", "Impact", "Segoe UI"]
        
    return fonts
