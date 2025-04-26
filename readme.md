# Credit Card Scraper

A utility for extracting credit card information from websites or PDF documents.

## Features

- Extract credit card details from websites with automatic structure detection
- Extract credit card details from PDF documents (bank brochures, etc.)
- OCR support for image-based PDFs using pytesseract
- Convert image-based PDFs to text-based PDFs
- Advanced pattern matching for varied document structures
- Support for additional credit card attributes (travel benefits, insurance, lounge access, etc.)
- Export results to multiple formats (JSON, CSV, Excel)
- Run locally without requiring external paid services
- Detailed logging for monitoring extraction progress

## Extracted Information

The scraper attempts to extract the following information for each credit card:

- Card name
- Issuing bank
- Joining fee
- Annual fee
- Reward structure
- Cashback offers
- Special offers
- Travel benefits (when available)
- Insurance coverage (when available)
- Airport lounge access (when available)
- Foreign transaction fees (when available)

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Tesseract OCR (for OCR capabilities with image-based PDFs)
- Poppler (for PDF to image conversion)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/credit-card-scraper.git
cd credit-card-scraper
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR:
   - For Windows: Download and install from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - For macOS: `brew install tesseract`
   - For Ubuntu/Debian: `sudo apt-get install tesseract-ocr`

5. Install Poppler:
   - For Windows: Download from [poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
   - For macOS: `brew install poppler`
   - For Ubuntu/Debian: `sudo apt-get install poppler-utils`

## Usage

### Basic Usage

```bash
python credit_card_scraper.py [source] [options]
```

Where `[source]` is a URL or path to a PDF file.

### Options

- `--output`, `-o`: Output filename (without extension). Default: `output`
- `--format`, `-f`: Output format (`json`, `csv`, `excel`, or `all`). Default: `all`
- `--convert-pdf`: Convert image-based PDF to text-based PDF (only applies to PDF sources)
- `--output-pdf`: Output path for converted PDF (only used with `--convert-pdf`)

### Examples

#### Extract from a website:

```bash
python credit_card_scraper.py https://example.com/credit-cards
```

#### Extract from a PDF file:

```bash
python credit_card_scraper.py path/to/credit_card_brochure.pdf
```

#### Convert image-based PDF and extract information:

```bash
python credit_card_scraper.py path/to/credit_card_brochure.pdf --convert-pdf --output-pdf converted_brochure.pdf
```

#### Specify output format:

```bash
python credit_card_scraper.py https://example.com/credit-cards --format json
```

#### Specify output filename:

```bash
python credit_card_scraper.py https://example.com/credit-cards --output my_cards
```

## Sample Outputs

The scraper will generate output files in the following formats (based on your selection):

- JSON: `output.json` (or your custom filename)
- CSV: `output.csv` (or your custom filename)
- Excel: `output.xlsx` (or your custom filename)

### Sample JSON Output

```json
[
    {
        "card_name": "Platinum Rewards Card",
        "issuing_bank": "Example Bank",
        "joining_fee": "$0",
        "annual_fee": "$95",
        "rewards": "2x points on dining and travel",
        "cashback": "1% on all purchases",
        "offers": "50,000 bonus points after spending $3,000 in first 3 months",
        "travel_benefits": "No foreign transaction fees",
        "insurance": "Travel insurance included",
        "lounge_access": "Priority Pass Select membership"
    },
    {
        "card_name": "Gold Travel Card",
        "issuing_bank": "Example Bank",
        "joining_fee": "$0",
        "annual_fee": "$250",
        "rewards": "3x points on airfare, 2x on restaurants",
        "cashback": null,
        "offers": "$100 annual travel credit",
        "foreign_transaction_fee": "0%"
    }
]
```

## Advanced Features

### OCR for Image-Based PDFs

The scraper can extract text from image-based PDFs using OCR technology:

```bash
python credit_card_scraper.py path/to/image_based.pdf
```

### PDF Conversion

Convert image-based PDFs to text-based PDFs:

```bash
python credit_card_scraper.py path/to/image_based.pdf --convert-pdf --output-pdf converted.pdf
```

## Dependencies

- requests: For fetching web pages
- BeautifulSoup4: For parsing HTML
- PyPDF2: For parsing PDF files
- pandas: For data manipulation and export to CSV/Excel
- openpyxl: For Excel file export
- pytesseract: For OCR capabilities
- pdf2image: For converting PDF to images
- reportlab: For creating text-based PDFs
- logging: For tracking extraction progress

## Limitations

- The scraper's ability to extract information depends on the structure of the website or PDF
- Some websites may have anti-scraping measures that could prevent the tool from working properly
- OCR quality depends on the clarity of the original document
- PDF extraction is based on text pattern matching and may not work for all PDF layouts or structures

## Future Improvements

- Add support for more complex website structures
- Improve PDF text extraction for varied layouts
- Add more robust error handling and recovery mechanisms
- Support for batch processing multiple sources
- Web interface for easier usage
- Support for additional document formats (e.g., Word, Excel)

## License

MIT License
