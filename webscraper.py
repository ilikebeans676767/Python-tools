#!/usr/bin/env python3
"""
Example usage of the WebsiteScraper class
This shows how to use the scraper programmatically
"""

from website_scraper import WebsiteScraper


def example_basic():
    """Basic example - download a website"""
    print("Example 1: Basic website download\n")
    
    scraper = WebsiteScraper(
        base_url="https://example.com",
        output_dir="example_download"
    )
    
    # Download the website (depth 2)
    scraper.scrape_bfs(max_depth=2)
    
    # Show statistics
    scraper.print_statistics()
    
    # Create zip file
    zip_file = scraper.create_zip("example.zip")
    print(f"\nCreated: {zip_file}")


def example_shallow_scrape():
    """Example - only download main page and direct resources"""
    print("Example 2: Shallow scrape (depth 1)\n")
    
    scraper = WebsiteScraper("https://example.com")
    
    # Only download the main page and its direct resources
    scraper.scrape_bfs(max_depth=1)
    
    scraper.print_statistics()
    scraper.create_zip("shallow.zip")


def example_custom_processing():
    """Example - custom processing with statistics"""
    print("Example 3: Custom processing\n")
    
    scraper = WebsiteScraper("https://example.com")
    
    # Scrape the site
    scraper.scrape_bfs(max_depth=2)
    
    # Access statistics
    total_files = sum(scraper.stats.values())
    print(f"\nDownloaded {total_files} files:")
    print(f"  - {scraper.stats['images']} images")
    print(f"  - {scraper.stats['css']} stylesheets")
    print(f"  - {scraper.stats['js']} scripts")
    
    # Create zip
    scraper.create_zip("custom.zip")


if __name__ == "__main__":
    print("=" * 60)
    print("Website Scraper - Examples")
    print("=" * 60)
    print("\nUncomment the example you want to run:\n")
    
    # Uncomment one of these to run:
    # example_basic()
    # example_shallow_scrape()
    # example_custom_processing()
    
    print("\nEdit this file to uncomment an example function.")
