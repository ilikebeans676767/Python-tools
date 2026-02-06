#!/usr/bin/env python3
"""
MP3 Crawler and Downloader
Searches a page and all pages one click away for MP3 files and downloads them
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import os
import re
from pathlib import Path
import time

def sanitize_filename(filename):
    """Clean up filename"""
    filename = unquote(filename)
    filename = os.path.basename(filename)
    filename = re.sub(r'^\d+[\s.-]*', '', filename)
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()[:200]
    
    if not filename or filename == '.mp3':
        filename = "audio.mp3"
    if not filename.lower().endswith('.mp3'):
        filename += '.mp3'
    
    return filename

def is_valid_mp3_url(url, base_domain):
    """Check if URL is valid and on same domain"""
    try:
        parsed = urlparse(url)
        base_parsed = urlparse(base_domain)
        
        # Must be same domain
        if parsed.netloc != base_parsed.netloc:
            return False
        
        # Must end in .mp3
        if not (parsed.path.lower().endswith('.mp3') or '.mp3?' in parsed.path.lower()):
            return False
        
        return True
    except:
        return False

def find_real_mp3_on_page(page_url, base_domain):
    """Look for actual MP3 download URLs on a single page"""
    mp3_urls = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Check audio tags - THIS IS THE KEY METHOD
        for audio in soup.find_all('audio'):
            src = audio.get('src')
            if src:
                full_url = urljoin(page_url, src)
                # Don't filter by domain - accept ANY mp3 URL
                if '.mp3' in src.lower():
                    mp3_urls.append(full_url)
            
            for source in audio.find_all('source'):
                src = source.get('src')
                if src:
                    full_url = urljoin(page_url, src)
                    if '.mp3' in src.lower():
                        mp3_urls.append(full_url)
        
        # Method 2: Check all links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '.mp3' in href.lower():
                full_url = urljoin(page_url, href)
                mp3_urls.append(full_url)
        
        # Method 3: Search page source for ANY mp3 URLs (even from different domains)
        page_source = response.text
        mp3_pattern = r'https?://[^\s<>"\']+\.mp3(?:\?[^\s<>"\']*)?'
        matches = re.findall(mp3_pattern, page_source, re.IGNORECASE)
        
        for match in matches:
            match = match.rstrip('",;)\']')
            mp3_urls.append(match)
        
        return list(set(mp3_urls))  # Remove duplicates
        
    except Exception as e:
        return []

def get_linked_pages(page_url, base_domain):
    """Get all pages linked from this page (one click away)"""
    linked_pages = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        base_parsed = urlparse(base_domain)
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(page_url, href)
            parsed = urlparse(full_url)
            
            # Only include links on same domain
            if parsed.netloc == base_parsed.netloc:
                # Include ALL links - even if they end in .mp3 (they're actually HTML pages with audio players)
                linked_pages.append(full_url)
        
        return list(set(linked_pages))  # Remove duplicates
        
    except Exception as e:
        return []

def download_mp3(mp3_url, output_dir, referer=None):
    """Download an actual MP3 file - handles both direct MP3s and HTML pages with audio players"""
    try:
        # IMPORTANT: The mp3_url might actually be an HTML page with an audio player
        # We need to check if it's HTML and extract the real MP3 URL if needed
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'audio/mpeg, audio/*, text/html, */*',
        }
        
        if referer:
            headers['Referer'] = referer
        
        print(f"    Processing: {os.path.basename(urlparse(mp3_url).path)}")
        
        # First, fetch the URL to see what it is
        response = requests.get(mp3_url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Check if we got HTML instead of audio
        if 'text/html' in content_type or response.content[:15].lower().startswith(b'<!doctype') or b'<html' in response.content[:100].lower():
            print(f"      → This is an HTML page, extracting real MP3 URL...")
            
            # Parse the HTML to find the audio tag
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for audio tag
            audio_tag = soup.find('audio')
            if audio_tag:
                real_mp3_url = audio_tag.get('src')
                if real_mp3_url:
                    real_mp3_url = urljoin(mp3_url, real_mp3_url)
                    print(f"      → Found real MP3: {real_mp3_url}")
                    
                    # Now download the REAL MP3
                    mp3_response = requests.get(real_mp3_url, headers=headers, stream=True, timeout=120, allow_redirects=True)
                    mp3_response.raise_for_status()
                    
                    filename = sanitize_filename(os.path.basename(urlparse(real_mp3_url).path))
                    filepath = os.path.join(output_dir, filename)
                    
                    # Handle duplicates
                    if os.path.exists(filepath):
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(filepath):
                            filename = f"{base}_{counter}{ext}"
                            filepath = os.path.join(output_dir, filename)
                            counter += 1
                    
                    print(f"      Downloading: {filename}")
                    
                    # Download the actual MP3
                    total_size = 0
                    with open(filepath, 'wb') as f:
                        for chunk in mp3_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                total_size += len(chunk)
                    
                    if total_size < 1000:
                        os.remove(filepath)
                        print(f"      ✗ File too small: {total_size} bytes")
                        return False
                    
                    print(f"      ✓ Downloaded! ({total_size / (1024*1024):.2f} MB)")
                    return True
                else:
                    print(f"      ✗ No src attribute in audio tag")
                    return False
            else:
                print(f"      ✗ No <audio> tag found in HTML")
                return False
        
        else:
            # It's already a direct MP3 file, save it
            filename = sanitize_filename(os.path.basename(urlparse(mp3_url).path))
            filepath = os.path.join(output_dir, filename)
            
            # Handle duplicates
            if os.path.exists(filepath):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(output_dir, filename)
                    counter += 1
            
            print(f"      Downloading: {filename}")
            
            total_size = len(response.content)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            if total_size < 1000:
                os.remove(filepath)
                print(f"      ✗ File too small: {total_size} bytes")
                return False
            
            print(f"      ✓ Downloaded! ({total_size / (1024*1024):.2f} MB)")
            return True
        
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False

def main():
    print("="*70)
    print("MP3 Crawler and Downloader")
    print("="*70)
    print("\nSearches a page AND all pages one click away for MP3 files")
    print()
    
    start_url = input("Enter the starting page URL: ").strip()
    
    if not start_url.startswith('http'):
        start_url = 'https://' + start_url
    
    output = input("Output folder (default='downloads'): ").strip() or "downloads"
    Path(output).mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("Starting search...")
    print(f"{'='*70}\n")
    
    base_domain = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    all_mp3s = set()
    downloaded_count = 0
    
    # Step 1: Search the main page
    print(f"[1] Searching main page: {start_url}")
    mp3s_on_main = find_real_mp3_on_page(start_url, base_domain)
    
    if mp3s_on_main:
        print(f"    Found {len(mp3s_on_main)} MP3(s) on main page")
        for mp3 in mp3s_on_main:
            if mp3 not in all_mp3s:
                all_mp3s.add(mp3)
                if download_mp3(mp3, output, referer=start_url):
                    downloaded_count += 1
                time.sleep(0.3)
    else:
        print(f"    No MP3s found on main page")
    
    # Step 2: Get all linked pages
    print(f"\n[2] Finding linked pages...")
    linked_pages = get_linked_pages(start_url, base_domain)
    print(f"    Found {len(linked_pages)} linked pages")
    
    # Step 3: Search each linked page
    if linked_pages:
        print(f"\n[3] Searching linked pages for MP3s...")
        print(f"    (Note: Pages ending in .mp3 are actually HTML with audio players)")
        
        for i, page_url in enumerate(linked_pages[:100], 1):  # Limit to first 100 pages
            print(f"\n    [{i}/{min(len(linked_pages), 100)}] Checking: {os.path.basename(page_url)}")
            
            mp3s_on_page = find_real_mp3_on_page(page_url, base_domain)
            
            if mp3s_on_page:
                print(f"        ✓ Found {len(mp3s_on_page)} MP3(s)")
                for mp3 in mp3s_on_page:
                    if mp3 not in all_mp3s:
                        all_mp3s.add(mp3)
                        if download_mp3(mp3, output, referer=page_url):
                            downloaded_count += 1
                        time.sleep(0.3)
            else:
                print(f"        No MP3s found on this page")
            
            time.sleep(0.2)  # Be nice to the server
    
    print(f"\n{'='*70}")
    print("Search Complete!")
    print(f"{'='*70}")
    print(f"Total MP3 URLs found: {len(all_mp3s)}")
    print(f"Successfully downloaded: {downloaded_count} files")
    print(f"Saved to: {os.path.abspath(output)}")
    print("="*70)

if __name__ == "__main__":
    main()
