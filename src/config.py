"""
Configuration settings for Google Maps Business Scraper.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "data/results")
    DEFAULT_LIMIT: int = int(os.getenv("DEFAULT_LIMIT", "50"))
    MIN_DELAY: float = float(os.getenv("MIN_DELAY", "0.5"))
    MAX_DELAY: float = float(os.getenv("MAX_DELAY", "1.5"))
    HEADLESS: bool = os.getenv("HEADLESS", "False").lower() == "true"
    FAST_MODE: bool = os.getenv("FAST_MODE", "True").lower() == "true"
    BLOCK_IMAGES: bool = os.getenv("BLOCK_IMAGES", "True").lower() == "true"
    
    @classmethod
    def ensure_output_dir(cls) -> Path:
        """Ensure the output directory exists and return its path."""
        output_path = Path(cls.OUTPUT_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path


# Realistic Chrome user agents for Windows and Mac
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    # Mac Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

# Common viewport sizes
VIEWPORTS = [
    {"width": 1920, "height": 1080},  # Full HD
    {"width": 1366, "height": 768},   # HD
    {"width": 1536, "height": 864},   # HD+
    {"width": 1440, "height": 900},   # WXGA+
    {"width": 1280, "height": 720},   # HD
    {"width": 1600, "height": 900},   # HD+
    {"width": 1680, "height": 1050},  # WSXGA+
    {"width": 2560, "height": 1440},  # QHD
]


# Create settings instance for easy import
settings = Settings()
