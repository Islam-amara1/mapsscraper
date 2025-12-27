# 🗺️ Google Maps Business Scraper

A powerful and fast Python scraper for extracting business data from Google Maps. Features anti-detection measures, stealth browsing, and multiple export formats.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Playwright](https://img.shields.io/badge/Playwright-Latest-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🚀 **Fast scraping** with optimized delays and resource blocking
- 🛡️ **Anti-detection** measures using playwright-stealth
- 📊 **Multiple export formats**: CSV, JSON, Excel
- 🎯 **Customizable** search queries and locations
- 💻 **Headless mode** for server deployment
- 🌐 **Rich CLI** with beautiful terminal output

## 📋 Data Extracted

For each business, the scraper extracts:
- Business name
- Rating (stars)
- Number of reviews
- Category/Type
- Address
- Phone number
- Website URL
- Google Maps URL

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/google-maps-scraper.git
cd google-maps-scraper
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install chromium
```

## 📖 Usage

### Basic Usage

```bash
# Scrape restaurants in Istanbul (10 results)
python -m src.main scrape "restaurants" -l "Istanbul" -n 10

# Scrape coffee shops in New York (50 results, headless mode)
python -m src.main scrape "coffee shops" -l "New York" -n 50 --headless

# Export to JSON format
python -m src.main scrape "hotels" -l "Paris" -n 20 -o json

# Export to all formats (CSV, JSON, Excel)
python -m src.main scrape "gyms" -l "London" -n 30 -o all
```

### Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--location` | `-l` | Location to search in | Required |
| `--limit` | `-n` | Maximum number of results | 50 |
| `--output` | `-o` | Output format (csv/json/excel/all) | csv |
| `--headless` | `-h` | Run browser in headless mode | False |

### Available Commands

```bash
# Show help
python -m src.main --help

# Show scrape command help
python -m src.main scrape --help

# Bulk scraping from file
python -m src.main bulk queries.txt

# Show version
python -m src.main version
```

## ⚙️ Configuration

Create a `.env` file based on `.env.example`:

```env
# Output directory for scraped data
OUTPUT_DIR=data/results

# Default number of results to scrape
DEFAULT_LIMIT=50

# Delay between requests (seconds)
MIN_DELAY=0.5
MAX_DELAY=1.5

# Run browser in headless mode
HEADLESS=False

# Block images for faster scraping
BLOCK_IMAGES=True
```

## 📁 Project Structure

```
google-maps-scraper/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI interface
│   ├── browser.py       # Stealth browser setup
│   ├── scraper.py       # Scraping logic
│   ├── exporter.py      # Data export (CSV, JSON, Excel)
│   └── config.py        # Configuration settings
├── data/
│   └── results/         # Scraped data output
├── requirements.txt
├── .env.example
└── README.md
```

## 📊 Output Example

```
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ #    ┃ Name                 ┃ Rating   ┃ Reviews    ┃ Phone           ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 1    │ Starbucks Coffee     │ 4.2⭐    │ 1,234      │ (212) 555-0123  │
│ 2    │ Blue Bottle Coffee   │ 4.5⭐    │ 856        │ (212) 555-0456  │
│ 3    │ Local Café           │ 4.8⭐    │ 342        │ (212) 555-0789  │
└──────┴──────────────────────┴──────────┴────────────┴─────────────────┘
```

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect Google's Terms of Service and use responsibly. The developers are not responsible for any misuse of this tool.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) - Browser automation
- [playwright-stealth](https://github.com/AtuboDad/playwright_stealth) - Anti-detection
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output
