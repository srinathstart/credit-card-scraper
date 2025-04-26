import argparse
import json
import os
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
import logging
from typing import List, Dict, Any, Union, Optional
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('credit_card_scraper')

class CreditCardScraper:
    """
    A scraper for extracting credit card information from websites or PDF documents.
    """
    
    def __init__(self):
        self.cards = []
        
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """
        Extract credit card information from the given source.
        
        Args:
            source: URL or path to a PDF file
            
        Returns:
            List of dictionaries containing credit card information
        """
        self.cards = []
        
        if source.startswith(('http://', 'https://')):
            logger.info(f"Processing URL: {source}")
            self._extract_from_url(source)
        elif source.lower().endswith('.pdf'):
            logger.info(f"Processing PDF: {source}")
            self._extract_from_pdf(source)
        else:
            logger.error(f"Unsupported source format: {source}")
            raise ValueError("Source must be a URL or a PDF file")
            
        return self.cards
    
    def _extract_from_url(self, url: str) -> None:
        """
        Extract credit card information from a website.
        
        Args:
            url: URL of the website
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Detect the type of website to determine the appropriate extraction strategy
            domain = urlparse(url).netloc
            
            # Extract based on common patterns
            self._extract_cards_from_html(soup, domain)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL: {e}")
            raise
    
    def _extract_from_pdf(self, pdf_path: str) -> None:
        """
        Extract credit card information from a PDF document.
        First tries using PyPDF2 for text extraction.
        If that yields insufficient text, uses OCR via pytesseract.
        
        Args:
            pdf_path: Path to the PDF file
        """
        try:
            # First try normal text extraction
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    text += page_text + "\n"
                
                # Check if we got meaningful text
                if len(text.strip()) < 100:  # Arbitrary threshold
                    logger.info("PDF appears to be image-based. Attempting OCR...")
                    text = self._ocr_pdf(pdf_path)
                
                # Extract credit card information from the text
                self._extract_cards_from_pdf_text(text)
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def _ocr_pdf(self, pdf_path: str) -> str:
        """
        Perform OCR on a PDF file to extract text from images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF images
        """
        try:
            # Convert PDF to images
            logger.info("Converting PDF to images...")
            images = convert_from_path(pdf_path)
            
            # Perform OCR on each image
            logger.info("Performing OCR on images...")
            text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                # Use pytesseract to extract text from the image
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Error during OCR: {e}")
            raise
    
    def _extract_cards_from_html(self, soup: BeautifulSoup, domain: str) -> None:
        """
        Extract credit card information from HTML content.
        
        Args:
            soup: BeautifulSoup object representing the HTML content
            domain: Domain name of the website
        """
        # General approach - look for sections or divs that contain card information
        # This will be adjusted based on the specific structure of the target website
        
        # Method 1: Look for card containers
        card_containers = soup.find_all(['div', 'section'], class_=lambda c: c and ('card' in c.lower() or 'product' in c.lower()))
        
        # Method 2: Look for card headings
        card_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'], text=lambda t: t and ('card' in t.lower() or 'credit' in t.lower()))
        
        # Method 3: Look for tables that might contain card information
        tables = soup.find_all('table')
        
        # Process card containers
        for container in card_containers:
            card = self._extract_card_from_container(container)
            if card and card not in self.cards:
                self.cards.append(card)
        
        # Process card headings
        for heading in card_headings:
            # Try to find the parent container that has the full card details
            parent = heading.find_parent(['div', 'section'])
            if parent:
                card = self._extract_card_from_container(parent)
                if card and card not in self.cards:
                    self.cards.append(card)
        
        # Process tables
        for table in tables:
            cards = self._extract_cards_from_table(table)
            for card in cards:
                if card and card not in self.cards:
                    self.cards.append(card)
        
        # If no cards are found, try a more general approach
        if not self.cards:
            # Look for text that might contain card information
            card_info_blocks = soup.find_all(['div', 'p', 'section'], text=lambda t: t and ('annual fee' in t.lower() or 'reward' in t.lower() or 'cashback' in t.lower()))
            
            for block in card_info_blocks:
                parent = block.find_parent(['div', 'section'])
                if parent:
                    card = self._extract_card_from_container(parent)
                    if card and card not in self.cards:
                        self.cards.append(card)
    
    def _extract_card_from_container(self, container) -> Optional[Dict[str, Any]]:
        """
        Extract a single credit card's information from an HTML container.
        
        Args:
            container: BeautifulSoup element containing card information
            
        Returns:
            Dictionary containing card information or None if extraction fails
        """
        card = {}
        
        # Extract card name
        name_tag = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
        if name_tag and name_tag.text.strip():
            card['card_name'] = name_tag.text.strip()
        else:
            # Try to find text that contains "card" and might be a card name
            for text in container.stripped_strings:
                if 'card' in text.lower() and len(text) < 100:  # Reasonable length for a card name
                    card['card_name'] = text.strip()
                    break
        
        # If we couldn't find a card name, this might not be a card container
        if 'card_name' not in card:
            return None
        
        # Extract issuing bank
        bank_keywords = ['bank', 'issuer', 'issuing bank']
        for keyword in bank_keywords:
            bank_tag = container.find(text=lambda t: t and keyword in t.lower())
            if bank_tag:
                parent = bank_tag.parent
                next_text = parent.next_sibling
                if next_text:
                    card['issuing_bank'] = next_text.strip()
                    break
        
        # Extract fees
        fee_patterns = {
            'joining_fee': [r'joining fee[:\s]*([₹$]?[\d,]+)', r'joining[:\s]*([₹$]?[\d,]+)'],
            'annual_fee': [r'annual fee[:\s]*([₹$]?[\d,]+)', r'annual[:\s]*([₹$]?[\d,]+)']
        }
        
        for fee_type, patterns in fee_patterns.items():
            for pattern in patterns:
                for text in container.stripped_strings:
                    match = re.search(pattern, text.lower())
                    if match:
                        card[fee_type] = match.group(1).strip()
                        break
                if fee_type in card:
                    break
        
        # Extract rewards
        reward_text = container.find(text=lambda t: t and 'reward' in t.lower())
        if reward_text:
            # Try to get the parent paragraph or container
            reward_parent = reward_text.parent
            if reward_parent:
                reward_info = ' '.join([text for text in reward_parent.stripped_strings])
                card['rewards'] = reward_info.strip()
        
        # Extract cashback
        cashback_text = container.find(text=lambda t: t and 'cashback' in t.lower())
        if cashback_text:
            # Try to get the parent paragraph or container
            cashback_parent = cashback_text.parent
            if cashback_parent:
                cashback_info = ' '.join([text for text in cashback_parent.stripped_strings])
                card['cashback'] = cashback_info.strip()
        
        # Extract offers
        offers_text = container.find(text=lambda t: t and 'offer' in t.lower())
        if offers_text:
            # Try to get the parent paragraph or container
            offers_parent = offers_text.parent
            if offers_parent:
                offers_info = ' '.join([text for text in offers_parent.stripped_strings])
                card['offers'] = offers_info.strip()
        
        return card
    
    def _extract_cards_from_table(self, table) -> List[Dict[str, Any]]:
        """
        Extract credit card information from an HTML table.
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            List of dictionaries containing card information
        """
        cards = []
        headers = []
        
        # Extract table headers
        header_row = table.find('tr')
        if header_row:
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.text.strip().lower())
        
        # If no headers found, try to infer them from the table structure
        if not headers:
            # Assume first column is card name, etc.
            headers = ['card_name', 'issuing_bank', 'joining_fee', 'annual_fee', 'rewards', 'cashback', 'offers']
        
        # Extract rows (skip the header row if it exists)
        rows = table.find_all('tr')[1:] if headers else table.find_all('tr')
        
        for row in rows:
            card = {}
            cells = row.find_all(['td', 'th'])
            
            # Map cell content to headers
            for i, cell in enumerate(cells):
                if i < len(headers):
                    header = headers[i]
                    # Map similar headers to our standard fields
                    if 'card' in header or 'name' in header:
                        card['card_name'] = cell.text.strip()
                    elif 'bank' in header or 'issuer' in header:
                        card['issuing_bank'] = cell.text.strip()
                    elif 'join' in header:
                        card['joining_fee'] = cell.text.strip()
                    elif 'annual' in header:
                        card['annual_fee'] = cell.text.strip()
                    elif 'reward' in header:
                        card['rewards'] = cell.text.strip()
                    elif 'cash' in header:
                        card['cashback'] = cell.text.strip()
                    elif 'offer' in header or 'benefit' in header:
                        card['offers'] = cell.text.strip()
                    else:
                        # Use the original header
                        card[header] = cell.text.strip()
            
            if card and card.get('card_name'):  # Only add if we have at least a card name
                cards.append(card)
        
        return cards
    
    def _extract_cards_from_pdf_text(self, text: str) -> None:
        """
        Extract credit card information from PDF text content.
        
        Args:
            text: Extracted text from PDF
        """
        # Log the first 200 characters of extracted text for debugging
        logger.info(f"Extracted text sample: {text[:200]}...")
        
        # Split text into sections that might represent different cards
        sections = re.split(r'\n\s*\n+', text)
        
        for section in sections:
            # Check if this section appears to be about a credit card
            if re.search(r'credit card|platinum card|gold card|rewards card|buzz card|travel card', section.lower()):
                card = {}
                
                # Extract card name - more comprehensive pattern
                card_name_patterns = [
                    r'([\w\s]+(?:Credit|Platinum|Gold|Rewards|Cashback|Signature|Infinite|World|Buzz|Travel)\s+Card)',
                    r'([A-Z][A-Za-z\s]+(?:CARD))',  # For cards like "AXIS BANK MY ZONE CREDIT CARD"
                    r'([\w\s]+Card)'  # Simpler fallback pattern
                ]
                
                for pattern in card_name_patterns:
                    card_name_match = re.search(pattern, section, re.IGNORECASE)
                    if card_name_match:
                        card['card_name'] = card_name_match.group(1).strip()
                        break
                
                # Extract issuing bank with improved patterns
                bank_patterns = [
                    r'([\w\s]+Bank)',
                    r'([\w\s]+Financial)',
                    r'([\w\s]+Express)',
                    r'(Axis)',
                    r'(ICICI)',
                    r'(HDFC)',
                    r'(SBI)',
                    r'(Citi)',
                    r'(American Express)',
                    r'([\w\s]+Banking)'
                ]
                
                for pattern in bank_patterns:
                    bank_match = re.search(pattern, section)
                    if bank_match:
                        card['issuing_bank'] = bank_match.group(1).strip()
                        break
                
                # Extract fees with improved patterns
                fee_patterns = {
                    'joining_fee': [
                        r'joining fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'joining[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'one[ -]?time fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'enrollment fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)'
                    ],
                    'annual_fee': [
                        r'annual fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'annual[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'yearly fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)',
                        r'renewal fee[:\s]*([₹$]?[\d,]+(?:\.\d+)?)'
                    ]
                }
                
                for fee_type, patterns in fee_patterns.items():
                    for pattern in patterns:
                        fee_match = re.search(pattern, section.lower())
                        if fee_match:
                            fee_value = fee_match.group(1).strip()
                            # Check for free or zero fees
                            if fee_value == '0' or fee_value == '$0' or fee_value == '₹0':
                                card[fee_type] = '$0'
                            else:
                                # Ensure consistent format with $ symbol if not present
                                if not fee_value.startswith(('$', '₹')):
                                    fee_value = '$' + fee_value
                                card[fee_type] = fee_value
                            break
                    # Set default values if not found
                    if fee_type not in card:
                        # Look for 'free' or 'nil' or 'waived' mentions
                        if re.search(rf'{fee_type.replace("_", " ")}[\s:]*(?:free|nil|waived|zero)', section.lower()):
                            card[fee_type] = '$0'
                
                # Extract rewards with improved patterns
                rewards_patterns = [
                    r'rewards?[:\s]*([\w\s.,\d%]+)',
                    r'reward points[:\s]*([\w\s.,\d%]+)',
                    r'points[:\s]*([\w\s.,\d%]+)',
                    r'(\d+[xX][\s\w]+(?:on|for)[\s\w]+)',  # Matches patterns like "2x points on dining"
                    r'earn[\s\w]+(\d+%|\d+[xX][\s\w]+)',   # Matches "earn 3x points" or "earn 2%"
                    r'miles[:\s]*([\w\s.,\d%]+)'
                ]
                
                for pattern in rewards_patterns:
                    rewards_match = re.search(pattern, section.lower())
                    if rewards_match:
                        reward_text = rewards_match.group(1).strip()
                        # Clean up the text: remove line breaks and extra spaces
                        reward_text = re.sub(r'\s+', ' ', reward_text)
                        card['rewards'] = reward_text
                        break
                
                # Extract cashback with improved patterns
                cashback_patterns = [
                    r'cashback[:\s]*([\w\s.,\d%]+)',
                    r'cash back[:\s]*([\w\s.,\d%]+)',
                    r'(\d+%\s*cash\s*back)',
                    r'(cash\s*back\s*of\s*\d+%)',
                    r'(earn\s*\d+%\s*cash)'
                ]
                
                for pattern in cashback_patterns:
                    cashback_match = re.search(pattern, section.lower())
                    if cashback_match:
                        cashback_text = cashback_match.group(1).strip()
                        # Clean up the text: remove line breaks and extra spaces
                        cashback_text = re.sub(r'\s+', ' ', cashback_text)
                        card['cashback'] = cashback_text
                        break
                
                # Extract special offers with improved patterns
                offers_patterns = [
                    r'offers?[:\s]*([\w\s.,\d%]+)',
                    r'benefits?[:\s]*([\w\s.,\d%]+)',
                    r'welcome\s*offers?[:\s]*([\w\s.,\d%]+)',
                    r'bonus[:\s]*([\w\s.,\d%]+)',
                    r'complimentary[:\s]*([\w\s.,\d%]+)',
                    r'free[:\s]*([\w\s.,\d%]+access)',
                    r'([\d,]+ bonus points after spending)',
                    r'([\d,]+ welcome points)',
                    r'(free [\w\s]+)'
                ]
                
                for pattern in offers_patterns:
                    offers_match = re.search(pattern, section.lower())
                    if offers_match:
                        offers_text = offers_match.group(1).strip()
                        # Clean up the text: remove line breaks and extra spaces
                        offers_text = re.sub(r'\s+', ' ', offers_text)
                        card['offers'] = offers_text
                        break
                
                # Additional specialized extractions
                
                # Travel benefits
                travel_match = re.search(r'travel[:\s]*([\w\s.,\d%]+)', section.lower())
                if travel_match:
                    card['travel_benefits'] = travel_match.group(1).strip()
                
                # Insurance coverage
                insurance_match = re.search(r'insurance[:\s]*([\w\s.,\d%]+)', section.lower())
                if insurance_match:
                    card['insurance'] = insurance_match.group(1).strip()
                
                # Airport lounge access
                lounge_match = re.search(r'lounge[:\s]*([\w\s.,\d%]+)', section.lower())
                if lounge_match:
                    card['lounge_access'] = lounge_match.group(1).strip()
                
                # Foreign transaction fee
                foreign_fee_match = re.search(r'foreign\s*transaction\s*fee[:\s]*([₹$]?[\d.,]+%?)', section.lower())
                if foreign_fee_match:
                    card['foreign_transaction_fee'] = foreign_fee_match.group(1).strip()
                
                # Set nulls for missing values to maintain consistent structure
                for field in ['rewards', 'cashback', 'offers', 'joining_fee', 'annual_fee']:
                    if field not in card:
                        card[field] = None
                
                # Only add the card if we have at least a name
                if card.get('card_name'):
                    # Remove any fields we added but don't want in the final output
                    # (Only if you want to stick strictly to the specified schema)
                    standard_fields = ['card_name', 'issuing_bank', 'joining_fee', 'annual_fee', 'rewards', 'cashback', 'offers']
                    extra_fields = [key for key in card.keys() if key not in standard_fields]
                    
                    # Uncomment the following line if you want to remove extra fields
                    # for field in extra_fields:
                    #     del card[field]
                    
                    self.cards.append(card)
    
    def save_to_json(self, output_path: str) -> None:
        """
        Save extracted credit card information to a JSON file.
        
        Args:
            output_path: Path to save the JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.cards, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved {len(self.cards)} cards to {output_path}")
    
    def save_to_csv(self, output_path: str) -> None:
        """
        Save extracted credit card information to a CSV file.
        
        Args:
            output_path: Path to save the CSV file
        """
        if not self.cards:
            logger.warning("No cards to save")
            return
            
        df = pd.DataFrame(self.cards)
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Saved {len(self.cards)} cards to {output_path}")
    
    def save_to_excel(self, output_path: str) -> None:
        """
        Save extracted credit card information to an Excel file.
        
        Args:
            output_path: Path to save the Excel file
        """
        if not self.cards:
            logger.warning("No cards to save")
            return
            
        df = pd.DataFrame(self.cards)
        df.to_excel(output_path, index=False)
        logger.info(f"Saved {len(self.cards)} cards to {output_path}")

    def convert_image_pdf_to_text(self, pdf_path: str, output_pdf_path: str = None) -> str:
        """
        Convert a PDF with images to a text-based PDF.
        
        Args:
            pdf_path: Path to the input PDF file
            output_pdf_path: Path to save the text-based PDF (optional)
            
        Returns:
            Path to the output PDF file or extracted text if no output path provided
        """
        try:
            # Convert PDF to images
            logger.info(f"Converting image-based PDF to text: {pdf_path}")
            images = convert_from_path(pdf_path)
            
            # Perform OCR on each image
            all_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                # Use pytesseract to extract text from the image
                page_text = pytesseract.image_to_string(image)
                all_text += page_text + "\n\n"
            
            # If output path is provided, create a new PDF with the extracted text
            if output_pdf_path:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.units import inch
                
                logger.info(f"Creating text-based PDF: {output_pdf_path}")
                
                doc = SimpleDocTemplate(
                    output_pdf_path,
                    pagesize=letter,
                    rightMargin=72, leftMargin=72,
                    topMargin=72, bottomMargin=72
                )
                
                styles = getSampleStyleSheet()
                style = styles["Normal"]
                
                # Split text into paragraphs
                paragraphs = []
                for para in all_text.split('\n\n'):
                    if para.strip():
                        paragraphs.append(Paragraph(para.replace('\n', '<br/>'), style))
                
                # Build the PDF
                doc.build(paragraphs)
                
                logger.info(f"Text-based PDF created successfully: {output_pdf_path}")
                return output_pdf_path
            else:
                return all_text
                
        except Exception as e:
            logger.error(f"Error during PDF conversion: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Extract credit card information from websites or PDF documents.')
    parser.add_argument('source', help='URL or path to a PDF file')
    parser.add_argument('--output', '-o', default='output', help='Output filename (without extension)')
    parser.add_argument('--format', '-f', choices=['json', 'csv', 'excel', 'all'], default='all', help='Output format')
    parser.add_argument('--convert-pdf', action='store_true', help='Convert image-based PDF to text-based PDF')
    parser.add_argument('--output-pdf', help='Output path for converted PDF (only used with --convert-pdf)')
    
    args = parser.parse_args()
    
    scraper = CreditCardScraper()
    
    try:
        if args.convert_pdf and args.source.lower().endswith('.pdf'):
            # Convert the PDF first
            output_pdf = args.output_pdf or args.source.replace('.pdf', '_text.pdf')
            converted_pdf = scraper.convert_image_pdf_to_text(args.source, output_pdf)
            
            # Then extract from the converted PDF
            cards = scraper.extract(converted_pdf)
        else:
            # Extract credit card information directly
            cards = scraper.extract(args.source)
        
        if not cards:
            logger.warning("No credit card information found.")
            return
        
        # Save to the specified format(s)
        if args.format in ['json', 'all']:
            scraper.save_to_json(f"{args.output}.json")
        
        if args.format in ['csv', 'all']:
            scraper.save_to_csv(f"{args.output}.csv")
        
        if args.format in ['excel', 'all']:
            scraper.save_to_excel(f"{args.output}.xlsx")
            
        logger.info(f"Successfully extracted information for {len(cards)} credit cards.")
        
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()