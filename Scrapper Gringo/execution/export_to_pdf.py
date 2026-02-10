#!/usr/bin/env python3
"""
export_to_pdf.py - Website to PDF Exporter

Crawls a website and all subpages, extracts content, and generates
a consolidated PDF document.

Usage:
    python export_to_pdf.py --url "https://docs.example.com" --output "docs.pdf"
    python export_to_pdf.py --url "https://snipki.de" --filter "/videos/" --limit 20
    
    # For JavaScript SPAs - provide URLs directly:
    python export_to_pdf.py --urls-file "urls.txt" --output "docs.pdf"
    
    # With browser mode for JavaScript sites:
    python export_to_pdf.py --url "https://spa-site.com" --browser

Requirements:
    pip install reportlab pypdf requests beautifulsoup4 python-dotenv
    
    # For browser mode (optional):
    pip install playwright && playwright install chromium
"""

import os
import sys
import re
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from collections import OrderedDict


try:
    import requests
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
except ImportError:
    print("Error: Missing base dependencies. Run:")
    print("  pip install requests beautifulsoup4 python-dotenv")
    sys.exit(1)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, ListFlowable, ListItem
    )
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
except ImportError:
    print("Error: Missing PDF dependencies. Run:")
    print("  pip install reportlab")
    sys.exit(1)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        print("Error: Missing PDF merge dependency. Run:")
        print("  pip install pypdf")
        sys.exit(1)

# Load environment variables
load_dotenv()

# Constants
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 1.5  # Polite delay between requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def setup_directories():
    """Create output directories."""
    base_dir = Path(__file__).parent.parent / ".tmp"
    parts_dir = base_dir / "pdf_parts"
    output_dir = base_dir / "pdf_output"
    
    base_dir.mkdir(exist_ok=True)
    parts_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    return parts_dir, output_dir


# Global browser instance for reuse
_browser_context = None


def get_browser():
    """Get or create a Playwright browser instance."""
    global _browser_context
    if _browser_context is None:
        try:
            from playwright.sync_api import sync_playwright
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            _browser_context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 720}
            )
        except ImportError:
            print("Error: Playwright not installed. Run:")
            print("  pip install playwright && playwright install chromium")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting browser: {e}")
            print("Try running: playwright install chromium")
            sys.exit(1)
    return _browser_context


def close_browser():
    """Close the browser instance."""
    global _browser_context
    if _browser_context:
        try:
            _browser_context.close()
        except:
            pass
        _browser_context = None


def fetch_page_browser(url: str, wait_time: int = 3000) -> tuple:
    """Fetch a webpage using Playwright browser (for JavaScript sites).
    
    Returns a BeautifulSoup object with additional '_browser_text' attribute
    containing the innerText for better text extraction.
    """
    try:
        if not url.startswith("http"):
            url = "https://" + url
        
        context = get_browser()
        page = context.new_page()
        
        try:
            page.goto(url, timeout=30000)
            # Wait for content to load
            page.wait_for_timeout(wait_time)
            
            # Try to wait for main content
            try:
                page.wait_for_selector("article, main, .content, h1", timeout=5000)
            except:
                pass
            
            # Extract text using JavaScript (much better for SPAs)
            extracted = page.evaluate('''() => {
                const result = {
                    title: '',
                    sections: []
                };
                
                // Get title
                const h1 = document.querySelector('h1');
                if (h1) {
                    result.title = h1.innerText.trim();
                } else {
                    result.title = document.title.split(' - ')[0].split(' | ')[0].trim();
                }
                
                // Find main content
                const main = document.querySelector('main') || 
                             document.querySelector('article') || 
                             document.querySelector('.content') ||
                             document.body;
                
                if (!main) return result;
                
                // Process all relevant elements in order
                const elements = main.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, pre, blockquote');
                
                elements.forEach(el => {
                    const tag = el.tagName.toLowerCase();
                    const text = el.innerText.trim();
                    
                    if (!text || text.length < 3) return;
                    
                    // Skip navigation and sidebar items
                    if (el.closest('nav') || 
                        el.closest('aside') || 
                        el.closest('header') || 
                        el.closest('footer') ||
                        el.closest('.sidebar') ||
                        el.closest('.nav') ||
                        el.closest('.menu') ||
                        el.closest('.toc') ||
                        el.closest('.table-of-contents') ||
                        el.closest('[role="navigation"]') ||
                        el.closest('mat-sidenav')) {
                        return;
                    }
                    
                    // Skip if parent matches common nav classes
                    const parent = el.parentElement;
                    if (parent && parent.className && 
                        (parent.className.includes('nav') || 
                         parent.className.includes('menu') || 
                         parent.className.includes('sidebar') ||
                         parent.className.includes('side_navigation'))) {
                        return;
                    }
                    

                    if (tag.startsWith('h')) {
                        result.sections.push({
                            type: 'heading',
                            level: parseInt(tag.charAt(1)),
                            text: text
                        });
                    } else if (tag === 'p' && text.length > 15) {
                        result.sections.push({
                            type: 'paragraph',
                            text: text
                        });
                    } else if (tag === 'li' && text.length > 10) {
                        // Add list items as paragraphs with bullet
                        result.sections.push({
                            type: 'list_item',
                            text: text
                        });
                    } else if (tag === 'pre') {
                        result.sections.push({
                            type: 'code',
                            text: text.substring(0, 1000)
                        });
                    } else if (tag === 'blockquote') {
                        result.sections.push({
                            type: 'quote',
                            text: text
                        });
                    }
                });
                
                return result;
            }''')
            
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Attach extracted data to soup for later use
            soup._browser_extracted = extracted
            
            return soup, None
        finally:
            page.close()
            
    except Exception as e:
        return None, str(e)


def fetch_page(url: str) -> tuple:
    """Fetch a webpage and return soup object."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup, None
    except Exception as e:
        return None, str(e)


def discover_urls(start_url: str, filter_pattern: str = None, 
                  max_depth: int = 2, max_urls: int = 50) -> list:
    """
    Stage 1: Discover all URLs to crawl.
    
    Args:
        start_url: Starting URL
        filter_pattern: Only include URLs containing this pattern
        max_depth: Maximum crawl depth
        max_urls: Maximum number of URLs to return
        
    Returns:
        List of URLs to process
    """
    print(f"\n🔍 Stage 1: Discovering URLs from {start_url}")
    print(f"   Filter: {filter_pattern or 'None'}")
    print(f"   Max depth: {max_depth}, Max URLs: {max_urls}\n")
    
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    base_url = f"{parsed_start.scheme}://{base_domain}"
    
    discovered = OrderedDict()  # URL -> depth
    discovered[start_url] = 0
    to_visit = [(start_url, 0)]
    
    while to_visit and len(discovered) < max_urls * 2:  # Get more, filter later
        current_url, depth = to_visit.pop(0)
        
        if depth >= max_depth:
            continue
        
        soup, error = fetch_page(current_url)
        if error:
            continue
        
        # Find all links on page
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Skip non-page links
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue
            if any(ext in href.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip']):
                continue
            
            # Make absolute URL
            if href.startswith('/'):
                href = urljoin(base_url, href)
            elif not href.startswith('http'):
                href = urljoin(current_url, href)
            
            # Check if same domain
            parsed_href = urlparse(href)
            if parsed_href.netloc != base_domain:
                continue
            
            # Clean URL (remove fragments and trailing slashes for dedup)
            clean_url = href.split('#')[0].rstrip('/')
            
            # Add if not seen
            if clean_url not in discovered:
                discovered[clean_url] = depth + 1
                to_visit.append((clean_url, depth + 1))
        
        # Small delay to be polite
        time.sleep(0.3)
    
    # Apply filter if specified
    urls = list(discovered.keys())
    if filter_pattern:
        urls = [u for u in urls if filter_pattern.lower() in u.lower()]
    
    # Limit results
    urls = urls[:max_urls]
    
    print(f"✅ Discovered {len(urls)} URLs")
    return urls


def extract_page_content(soup: BeautifulSoup, url: str) -> dict:
    """
    Extract content from a single page.
    
    Returns:
        Dictionary with title, content blocks, and metadata
    """
    # Check if we have browser-extracted data (better for SPAs)
    if hasattr(soup, '_browser_extracted') and soup._browser_extracted:
        extracted = soup._browser_extracted
        return {
            'url': url,
            'title': extracted.get('title', ''),
            'sections': extracted.get('sections', [])
        }
    
    # Fall back to BeautifulSoup extraction for static pages
    content = {
        'url': url,
        'title': '',
        'sections': [],  # List of content sections
    }

    
    # Get title - try multiple sources
    h1 = soup.find('h1')
    if h1:
        content['title'] = h1.get_text(separator=' ', strip=True)
    else:
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Remove common suffixes like " - Site Name"
            if ' - ' in title_text:
                title_text = title_text.split(' - ')[0]
            elif ' | ' in title_text:
                title_text = title_text.split(' | ')[0]
            content['title'] = title_text
    
    # Find main content area - try specific selectors first
    main_content = None
    selectors = [
        'main article',
        'main .content',
        'article',
        'main',
        '.docs-content',
        '.doc-content', 
        '.markdown-body',
        '.post-content',
        '.entry-content',
        '.article-content',
        '.page-content',
        '[role="main"]',
    ]
    
    for selector in selectors:
        main_content = soup.select_one(selector)
        if main_content:
            # Check if it has actual text content
            text = main_content.get_text(strip=True)
            if len(text) > 100:  # Has meaningful content
                break
            main_content = None
    
    if not main_content:
        main_content = soup.body or soup
    
    # Create a copy to avoid modifying original
    from copy import copy
    main_content = copy(main_content)
    
    # Remove unwanted elements
    unwanted_selectors = [
        'script', 'style', 'noscript', 'iframe',
        'nav', 'header', 'footer', 'aside',
        '.sidebar', '.menu', '.navigation', '.nav',
        '.comments', '.ad', '.advertisement',
        '.cookie-banner', '.popup', '.modal',
        '[role="navigation"]', '[role="banner"]',
        '.toc', '.table-of-contents', '.on-this-page',
    ]
    
    for selector in unwanted_selectors:
        for unwanted in main_content.select(selector):
            unwanted.decompose()
    
    # Track what we've already processed to avoid duplicates
    processed_texts = set()
    
    # Process elements in document order
    def process_element(element):
        """Process a single element and its direct content."""
        if not hasattr(element, 'name') or element.name is None:
            return
        
        tag = element.name
        
        # Handle headings
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(separator=' ', strip=True)
            if text and text not in processed_texts and len(text) > 1:
                processed_texts.add(text)
                content['sections'].append({
                    'type': 'heading',
                    'level': int(tag[1]),
                    'text': text
                })
        
        # Handle paragraphs
        elif tag == 'p':
            text = element.get_text(separator=' ', strip=True)
            # Skip short or duplicate text
            if text and len(text) > 15 and text not in processed_texts:
                processed_texts.add(text)
                content['sections'].append({
                    'type': 'paragraph',
                    'text': text
                })
        
        # Handle lists
        elif tag in ['ul', 'ol']:
            items = []
            for li in element.find_all('li', recursive=False):
                item_text = li.get_text(separator=' ', strip=True)
                if item_text and item_text not in processed_texts:
                    processed_texts.add(item_text)
                    items.append(item_text)
            
            if items:
                content['sections'].append({
                    'type': 'list',
                    'ordered': tag == 'ol',
                    'items': items
                })
        
        # Handle code blocks
        elif tag == 'pre':
            code = element.find('code')
            if code:
                text = code.get_text(strip=True)
            else:
                text = element.get_text(strip=True)
            
            if text and text not in processed_texts and len(text) > 5:
                processed_texts.add(text)
                content['sections'].append({
                    'type': 'code',
                    'text': text[:1000]  # Limit code block size
                })
        
        # Handle blockquotes
        elif tag == 'blockquote':
            text = element.get_text(separator=' ', strip=True)
            if text and text not in processed_texts:
                processed_texts.add(text)
                content['sections'].append({
                    'type': 'quote',
                    'text': text
                })
        
        # Handle divs and other containers - only if they have direct text
        elif tag in ['div', 'section', 'span']:
            # Only process if it contains direct text (not just nested elements)
            direct_text = ''.join(
                child.strip() for child in element.strings 
                if child.parent == element
            ).strip()
            
            # If div has substantial direct text and no block children
            if direct_text and len(direct_text) > 30:
                has_block_children = any(
                    child.name in ['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre', 'blockquote']
                    for child in element.children if hasattr(child, 'name')
                )
                if not has_block_children and direct_text not in processed_texts:
                    processed_texts.add(direct_text)
                    content['sections'].append({
                        'type': 'paragraph',
                        'text': direct_text
                    })
    
    # Walk through all elements in document order
    for element in main_content.find_all(True):  # True = all tags
        process_element(element)
    
    # If we still have no content, try a simpler extraction
    if not content['sections']:
        # Get all text from main content
        all_text = main_content.get_text(separator='\n', strip=True)
        
        # Split into paragraphs and filter
        paragraphs = [p.strip() for p in all_text.split('\n') if p.strip()]
        
        for para in paragraphs:
            if len(para) > 30:  # Only meaningful paragraphs
                content['sections'].append({
                    'type': 'paragraph',
                    'text': para
                })
    
    return content


def create_page_pdf(content: dict, output_path: Path) -> bool:
    """
    Create a PDF for a single page.
    
    Args:
        content: Page content dictionary
        output_path: Path to save PDF
        
    Returns:
        True if successful
    """
    try:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2.5*cm,
            rightMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a2e'),
            fontName='Helvetica-Bold'
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e'),
            fontName='Helvetica-Bold'
        )
        
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor('#0f3460'),
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Times-Roman'
        )
        
        url_style = ParagraphStyle(
            'UrlStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20
        )
        
        # Build content
        story = []
        
        # Title
        if content['title']:
            # Escape special characters for ReportLab
            safe_title = content['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_title, title_style))
        
        # Source URL
        safe_url = content['url'].replace('&', '&amp;')
        story.append(Paragraph(f"Quelle: {safe_url}", url_style))
        story.append(Spacer(1, 10))
        
        # Content sections
        for section in content['sections']:
            if section['type'] == 'heading':
                level = section['level']
                text = section['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                if level <= 2:
                    story.append(Paragraph(text, h2_style))
                else:
                    story.append(Paragraph(text, h3_style))
            
            elif section['type'] == 'paragraph':
                text = section['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    story.append(Paragraph(text, body_style))
                except:
                    # Skip problematic paragraphs
                    pass
            
            elif section['type'] == 'list':
                items = []
                for item_text in section['items'][:20]:  # Limit list items
                    safe_text = item_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    try:
                        items.append(ListItem(Paragraph(safe_text, body_style)))
                    except:
                        pass
                
                if items:
                    bullet_type = 'I' if section['ordered'] else 'bullet'
                    story.append(ListFlowable(items, bulletType=bullet_type))
                    story.append(Spacer(1, 10))
            
            elif section['type'] == 'code':
                # Code block style
                code_style = ParagraphStyle(
                    'CodeStyle',
                    parent=styles['Code'],
                    fontSize=9,
                    fontName='Courier',
                    backColor=colors.HexColor('#f5f5f5'),
                    borderColor=colors.HexColor('#e0e0e0'),
                    borderWidth=1,
                    borderPadding=8,
                    spaceBefore=10,
                    spaceAfter=10,
                    leftIndent=10,
                    rightIndent=10,
                )
                text = section['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # Replace newlines with <br/> for PDF
                text = text.replace('\n', '<br/>')
                try:
                    story.append(Paragraph(f"<font face='Courier' size='9'>{text}</font>", code_style))
                except:
                    pass
            
            elif section['type'] == 'quote':
                # Blockquote style
                quote_style = ParagraphStyle(
                    'QuoteStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    fontName='Times-Italic',
                    textColor=colors.HexColor('#555555'),
                    leftIndent=20,
                    rightIndent=20,
                    spaceBefore=10,
                    spaceAfter=10,
                    borderColor=colors.HexColor('#cccccc'),
                    borderWidth=0,
                    borderPadding=5,
                )
                text = section['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    story.append(Paragraph(f"<i>{text}</i>", quote_style))
                except:
                    pass
            
            elif section['type'] == 'list_item':
                # Individual list item (from browser extraction)
                text = section['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    story.append(Paragraph(f"• {text}", body_style))
                except:
                    pass
        
        # Build PDF
        if story:
            doc.build(story)
            return True
        return False
        
    except Exception as e:
        print(f"      ⚠️ PDF error: {str(e)[:50]}")
        return False


def merge_pdfs(pdf_paths: list, output_path: Path, toc_entries: list) -> bool:
    """
    Merge multiple PDFs into one with table of contents.
    
    Args:
        pdf_paths: List of PDF paths to merge
        output_path: Path for output PDF
        toc_entries: List of (title, page_number) for TOC
        
    Returns:
        True if successful
    """
    print(f"\n📚 Stage 3: Merging {len(pdf_paths)} PDFs...")
    
    try:
        # First, create a TOC PDF
        toc_path = output_path.parent / "_toc_temp.pdf"
        create_toc_pdf(toc_entries, toc_path)
        
        # Merge all PDFs
        writer = PdfWriter()
        
        # Add TOC first
        if toc_path.exists():
            toc_reader = PdfReader(str(toc_path))
            for page in toc_reader.pages:
                writer.add_page(page)
        
        # Add content PDFs
        for pdf_path in pdf_paths:
            try:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                print(f"   ⚠️ Skipping {pdf_path.name}: {e}")
        
        # Save merged PDF
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        # Clean up TOC temp file
        if toc_path.exists():
            toc_path.unlink()
        
        print(f"✅ Merged PDF saved: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Merge error: {e}")
        return False


def create_toc_pdf(entries: list, output_path: Path):
    """Create a table of contents PDF."""
    try:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2.5*cm,
            rightMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TOCTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a2e')
        )
        
        entry_style = ParagraphStyle(
            'TOCEntry',
            parent=styles['Normal'],
            fontSize=11,
            leading=18,
            leftIndent=20
        )
        
        story = []
        story.append(Paragraph("Inhaltsverzeichnis", title_style))
        story.append(Spacer(1, 20))
        
        for i, (title, _) in enumerate(entries, 1):
            safe_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # Truncate long titles
            if len(safe_title) > 70:
                safe_title = safe_title[:67] + "..."
            story.append(Paragraph(f"{i}. {safe_title}", entry_style))
        
        story.append(PageBreak())
        doc.build(story)
        
    except Exception as e:
        print(f"   ⚠️ TOC creation failed: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export website to PDF document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python export_to_pdf.py --url "https://docs.example.com"

  # With filter and limits
  python export_to_pdf.py --url "https://snipki.de" \\
      --filter "/videos/" --depth 2 --limit 20

  # Custom output name, keep individual PDFs
  python export_to_pdf.py --url "https://example.com/docs/" \\
      --output "documentation.pdf" --keep-parts

  # For JavaScript SPAs - use browser mode
  python export_to_pdf.py --url "https://spa-site.com/docs" --browser

  # Provide URLs directly from a file (one URL per line)
  python export_to_pdf.py --urls-file "urls.txt" --output "docs.pdf"
        """
    )
    
    # URL source options (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-u", "--url",
                        help="Starting URL to crawl")
    source.add_argument("--urls-file",
                        help="File containing URLs to process (one per line)")
    
    parser.add_argument("-f", "--filter",
                        help="Only include URLs containing this pattern")
    parser.add_argument("-d", "--depth", type=int, default=2,
                        help="Maximum crawl depth (default: 2)")
    parser.add_argument("-n", "--limit", type=int, default=50,
                        help="Maximum pages to include (default: 50)")
    parser.add_argument("-o", "--output",
                        help="Output filename (default: auto-generated)")
    parser.add_argument("--keep-parts", action="store_true",
                        help="Keep individual page PDFs")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY,
                        help=f"Delay between requests (default: {REQUEST_DELAY}s)")
    parser.add_argument("--browser", action="store_true",
                        help="Use browser to render JavaScript (requires playwright)")
    parser.add_argument("--wait", type=int, default=3000,
                        help="Wait time in ms for JS rendering (default: 3000, only with --browser)")
    
    args = parser.parse_args()
    
    # Setup directories
    parts_dir, output_dir = setup_directories()
    
    # Determine fetch function based on mode
    if args.browser:
        print("🌐 Browser mode enabled (for JavaScript sites)")
        fetch_func = lambda url: fetch_page_browser(url, args.wait)
    else:
        fetch_func = fetch_page
    
    # Stage 1: Get URLs
    urls = []
    
    if args.urls_file:
        # Read URLs from file
        urls_file = Path(args.urls_file)
        if not urls_file.exists():
            print(f"❌ URLs file not found: {args.urls_file}")
            sys.exit(1)
        
        print(f"\n📋 Reading URLs from {args.urls_file}")
        with open(urls_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
        
        # Apply filter if specified
        if args.filter:
            urls = [u for u in urls if args.filter.lower() in u.lower()]
        
        urls = urls[:args.limit]
        print(f"✅ Loaded {len(urls)} URLs")
        
    else:
        # Discover URLs by crawling
        if args.browser:
            # Browser-based discovery
            print(f"\n🔍 Stage 1: Discovering URLs from {args.url} (browser mode)")
            print(f"   Filter: {args.filter or 'None'}")
            print(f"   Max depth: {args.depth}, Max URLs: {args.limit}\n")
            
            parsed_start = urlparse(args.url)
            base_domain = parsed_start.netloc
            base_url = f"{parsed_start.scheme}://{base_domain}"
            
            discovered = OrderedDict()
            discovered[args.url] = 0
            to_visit = [(args.url, 0)]
            
            while to_visit and len(discovered) < args.limit * 2:
                current_url, depth = to_visit.pop(0)
                
                if depth >= args.depth:
                    continue
                
                soup, error = fetch_func(current_url)
                if error:
                    print(f"   ⚠️ Skip: {current_url[:40]}... ({error[:30]})")
                    continue
                
                print(f"   ✓ Scanned: {current_url[:50]}...")
                
                # Find all links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    
                    if href.startswith('#') or href.startswith('javascript:'):
                        continue
                    if href.startswith('mailto:') or href.startswith('tel:'):
                        continue
                    if any(ext in href.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip']):
                        continue
                    
                    if href.startswith('/'):
                        href = urljoin(base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(current_url, href)
                    
                    parsed_href = urlparse(href)
                    if parsed_href.netloc != base_domain:
                        continue
                    
                    clean_url = href.split('#')[0].rstrip('/')
                    
                    if clean_url not in discovered:
                        discovered[clean_url] = depth + 1
                        to_visit.append((clean_url, depth + 1))
                
                time.sleep(0.5)  # Slightly longer delay for browser
            
            urls = list(discovered.keys())
            if args.filter:
                urls = [u for u in urls if args.filter.lower() in u.lower()]
            urls = urls[:args.limit]
            print(f"\n✅ Discovered {len(urls)} URLs")
            
        else:
            # Standard HTTP discovery
            urls = discover_urls(
                start_url=args.url,
                filter_pattern=args.filter,
                max_depth=args.depth,
                max_urls=args.limit
            )
    
    if not urls:
        print("❌ No URLs found to process")
        sys.exit(1)
    
    # Stage 2: Extract content and create individual PDFs
    print(f"\n📄 Stage 2: Creating PDFs for {len(urls)} pages")
    print(f"   Mode: {'Browser' if args.browser else 'HTTP'}")
    print(f"   Delay: {args.delay}s between requests\n")
    
    pdf_paths = []
    toc_entries = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        for i, url in enumerate(urls, 1):
            print(f"   [{i}/{len(urls)}] {url[:60]}...")
            
            soup, error = fetch_func(url)
            if error:
                print(f"      ⚠️ Skipped: {error[:40]}")
                continue
            
            # Extract content
            content = extract_page_content(soup, url)
            
            if not content['sections']:
                print(f"      ⚠️ No content found")
                continue
            
            # Create PDF
            safe_name = re.sub(r'[^\w\-]', '_', urlparse(url).path)[:50] or 'index'
            pdf_filename = f"{i:03d}_{safe_name}.pdf"
            pdf_path = parts_dir / pdf_filename
            
            if create_page_pdf(content, pdf_path):
                pdf_paths.append(pdf_path)
                toc_entries.append((content['title'] or url, len(pdf_paths)))
                print(f"      ✓ {content['title'][:40] if content['title'] else 'Created'}")
            
            # Polite delay
            if i < len(urls):
                time.sleep(args.delay)
    
    finally:
        # Clean up browser if used
        if args.browser:
            close_browser()
    
    if not pdf_paths:
        print("\n❌ No PDFs were created")
        sys.exit(1)
    
    print(f"\n✅ Created {len(pdf_paths)} individual PDFs")
    
    # Stage 3: Merge PDFs
    if args.output:
        output_filename = args.output
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
    else:
        if args.url:
            domain = urlparse(args.url).netloc.replace('.', '_')[:20]
        else:
            domain = Path(args.urls_file).stem[:20]
        output_filename = f"{domain}_{timestamp}.pdf"
    
    output_path = output_dir / output_filename
    
    if merge_pdfs(pdf_paths, output_path, toc_entries):
        print(f"\n📁 Final PDF: {output_path}")
        print(f"   Pages: {len(pdf_paths)} sections")
        
        # Clean up individual PDFs if not keeping
        if not args.keep_parts:
            print("\n🧹 Cleaning up individual PDFs...")
            for pdf_path in pdf_paths:
                try:
                    pdf_path.unlink()
                except:
                    pass
    else:
        print(f"\n⚠️ Merge failed. Individual PDFs saved in: {parts_dir}")


if __name__ == "__main__":
    main()

