import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
import urllib.parse
from datetime import datetime

def scrape_billboard_india():
    """
    Scrape Billboard India Hot Songs chart and extract top 20 hits
    """
    url = "https://www.billboard.com/charts/india-songs-hotw/"
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main chart container with the correct class
        chart_rows = soup.find_all('ul', class_='o-chart-results-list-row')
        
        songs_data = []
        
        print(f"Found {len(chart_rows)} chart entries")
        
        for i, row in enumerate(chart_rows[:20]):  # Get top 20
            try:
                # Extract position from the first li element with position number
                position_elem = row.find('span', class_='c-label')
                if position_elem and position_elem.get_text().strip().isdigit():
                    position = int(position_elem.get_text().strip())
                else:
                    position = i + 1
                
                # Extract song title - look for h3 with c-title class
                title_elem = row.find('h3', class_='c-title')
                if title_elem:
                    title = title_elem.get_text().strip()
                else:
                    title = "N/A"
                
                # Extract artist - look for span with c-label class that contains artist name
                # This is usually the second c-label span after the position
                artist_spans = row.find_all('span', class_='c-label')
                artist = "N/A"
                
                # Look through all spans to find the artist (usually contains text, not just numbers)
                for span in artist_spans:
                    span_text = span.get_text().strip()
                    # Skip if it's just a number (position) or empty
                    if span_text and not span_text.isdigit() and span_text not in ['LW', 'PEAK', 'WEEKS']:
                        artist = span_text
                        break
                
                # If still no artist found, try alternative method
                if artist == "N/A":
                    # Look for the artist in the structure after the title
                    title_parent = title_elem.parent if title_elem else None
                    if title_parent:
                        next_span = title_parent.find_next('span', class_='c-label')
                        if next_span:
                            candidate_artist = next_span.get_text().strip()
                            if candidate_artist and not candidate_artist.isdigit():
                                artist = candidate_artist
                
                # Extract last week position - look for LW data
                last_week = "NEW"
                lw_indicators = row.find_all(string=re.compile(r'LW|Last Week', re.I))
                if lw_indicators:
                    # Find the span that comes after LW indicator
                    for indicator in lw_indicators:
                        parent = indicator.parent
                        if parent:
                            next_elem = parent.find_next('span', class_='c-label')
                            if next_elem:
                                lw_text = next_elem.get_text().strip()
                                if lw_text.isdigit():
                                    last_week = lw_text
                                    break
                
                # Clean up the data
                title = re.sub(r'\s+', ' ', title).strip()
                artist = re.sub(r'\s+', ' ', artist).strip()
                
                # Skip if we couldn't extract basic info
                if title == "N/A" or not title:
                    continue
                
                songs_data.append({
                    'Position': position,
                    'Song': title,
                    'Artist': artist,
                    'Last Week': last_week
                })
                
                print(f"✅ Scraped: {position}. {title} - {artist} (LW: {last_week})")
                
            except Exception as e:
                print(f"❌ Error extracting data for row {i+1}: {e}")
                continue
        
        # If we got less than expected, try alternative parsing method
        if len(songs_data) < 10:
            print("🔄 Trying alternative parsing method...")
            return scrape_billboard_alternative(soup)
        
        print(f"✅ Successfully scraped {len(songs_data)} songs")
        return songs_data
        
    except requests.RequestException as e:
        print(f"❌ Error fetching the page: {e}")
        return []

def scrape_billboard_alternative(soup):
    """
    Alternative scraping method using the text content pattern
    """
    songs_data = []
    
    try:
        # Get all text and parse it line by line
        text_content = soup.get_text()
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        position = 1
        i = 0
        
        while i < len(lines) and position <= 20:
            try:
                # Look for position numbers
                if lines[i].isdigit() and int(lines[i]) == position:
                    # Found position, now look for song title and artist
                    song_title = None
                    artist = None
                    last_week = "NEW"
                    
                    # Look ahead for song title (usually a few lines after position)
                    for j in range(i+1, min(i+10, len(lines))):
                        line = lines[j]
                        
                        # Skip common chart elements
                        if line in ['LW', 'PEAK', 'WEEKS', '-'] or line.isdigit():
                            continue
                        
                        # Check if this looks like a song title
                        if not song_title and len(line) > 3 and not line.startswith('http'):
                            # Additional checks to ensure it's likely a song title
                            if '(' in line or line.istitle() or any(word.istitle() for word in line.split()):
                                song_title = line
                                continue
                        
                        # Check if this looks like an artist name
                        if song_title and not artist and len(line) > 2:
                            # Skip if it's a number or common chart element
                            if not line.isdigit() and line not in ['LW', 'PEAK', 'WEEKS', '-']:
                                artist = line
                                break
                    
                    if song_title:
                        songs_data.append({
                            'Position': position,
                            'Song': song_title,
                            'Artist': artist or "N/A",
                            'Last Week': last_week
                        })
                        print(f"✅ Alt method: {position}. {song_title} - {artist or 'N/A'}")
                        position += 1
                    
                i += 1
                
            except Exception as e:
                print(f"❌ Error in alternative parsing at line {i}: {e}")
                i += 1
                continue
        
        return songs_data
        
    except Exception as e:
        print(f"❌ Error in alternative scraping method: {e}")
        return []

def create_html_table(songs_data):
    """
    Create an HTML table from the songs data with Billboard-style design
    """
    if not songs_data:
        return "<p>❌ No chart data available. The website structure may have changed.</p>"
    
    # URL encode function for search queries
    def url_encode(text):
        import urllib.parse
        return urllib.parse.quote(text)
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 900px; margin: 0 auto; background: #ffffff;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #d41367, #ff1744); padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 32px; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">Billboard</h1>
            <h2 style="color: white; margin: 10px 0 0 0; font-size: 24px; font-weight: 400; opacity: 0.95;">India Songs</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 16px;">Hot This Week • Chart Date: {datetime.now().strftime("%B %d, %Y")}</p>
        </div>
        
        <!-- Chart Table -->
        <div style="background: #ffffff; border-radius: 0 0 8px 8px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            <table style="width: 100%; border-collapse: collapse; font-family: inherit;">
                <thead style="background: #f8f9fa; border-bottom: 2px solid #e9ecef;">
                    <tr>
                        <th style="padding: 16px 12px; text-align: center; width: 60px; font-weight: 700; color: #495057; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Rank</th>
                        <th style="padding: 16px 20px; text-align: left; font-weight: 700; color: #495057; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Song</th>
                        <th style="padding: 16px 20px; text-align: left; width: 220px; font-weight: 700; color: #495057; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Artist</th>
                        <th style="padding: 16px 12px; text-align: center; width: 80px; font-weight: 700; color: #495057; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Last<br>Week</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, song in enumerate(songs_data):
        # Alternate row colors like Billboard
        row_bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        
        # Position styling - Billboard uses pink/red for top positions
        if song['Position'] == 1:
            position_bg = "#d41367"
            position_color = "white"
            position_style = f"background: {position_bg}; color: {position_color}; font-weight: 800; border-radius: 50%; width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center; font-size: 18px;"
        elif song['Position'] <= 5:
            position_bg = "#ff6b9d"
            position_color = "white"
            position_style = f"background: {position_bg}; color: {position_color}; font-weight: 700; border-radius: 50%; width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center; font-size: 16px;"
        elif song['Position'] <= 10:
            position_bg = "#6c757d"
            position_color = "white"
            position_style = f"background: {position_bg}; color: {position_color}; font-weight: 600; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-size: 14px;"
        else:
            position_style = f"color: #495057; font-weight: 600; font-size: 16px;"
        
        # Last week indicator styling
        if song['Last Week'] == 'NEW':
            lw_style = "background: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;"
            lw_text = "NEW"
        elif song['Last Week'].isdigit():
            current_pos = song['Position']
            last_pos = int(song['Last Week'])
            if current_pos < last_pos:
                # Moved up
                lw_style = "color: #28a745; font-weight: 600; font-size: 13px;"
                lw_text = f"▲ {song['Last Week']}"
            elif current_pos > last_pos:
                # Moved down  
                lw_style = "color: #dc3545; font-weight: 600; font-size: 13px;"
                lw_text = f"▼ {song['Last Week']}"
            else:
                # No change
                lw_style = "color: #6c757d; font-weight: 500; font-size: 13px;"
                lw_text = f"— {song['Last Week']}"
        else:
            lw_style = "color: #6c757d; font-weight: 400; font-size: 12px;"
            lw_text = song['Last Week']
        
        # Create search URLs
        search_query = f"{song['Song']} {song['Artist']}"
        google_search_url = f"https://www.google.com/search?q={url_encode(search_query)}"
        spotify_search_url = f"https://open.spotify.com/search/{url_encode(search_query)}"
        
        html += f"""
            <tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef; transition: background-color 0.2s ease;">
                <td style="padding: 16px 12px; text-align: center; vertical-align: middle;">
                    <span style="{position_style}">{song['Position']}</span>
                </td>
                <td style="padding: 16px 20px; vertical-align: middle;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="flex-grow: 1;">
                            <div style="font-size: 16px; font-weight: 600; color: #212529; line-height: 1.3; margin-bottom: 2px;">
                                {song['Song']}
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px; flex-shrink: 0;">
                            <a href="{google_search_url}" target="_blank" style="display: inline-block; padding: 6px; border-radius: 4px; background: #f8f9fa; border: 1px solid #dee2e6; text-decoration: none; transition: all 0.2s ease;" title="Search on Google">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                                </svg>
                            </a>
                            <a href="{spotify_search_url}" target="_blank" style="display: inline-block; padding: 6px; border-radius: 4px; background: #1db954; border: 1px solid #1db954; text-decoration: none; transition: all 0.2s ease;" title="Search on Spotify">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                                </svg>
                            </a>
                        </div>
                    </div>
                </td>
                <td style="padding: 16px 20px; vertical-align: middle;">
                    <div style="color: #6c757d; font-size: 15px; font-weight: 500; line-height: 1.3;">
                        {song['Artist']}
                    </div>
                </td>
                <td style="padding: 16px 12px; text-align: center; vertical-align: middle;">
                    <span style="{lw_style}">{lw_text}</span>
                </td>
            </tr>
        """
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div style="padding: 20px; text-align: center; background: #f8f9fa; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
            <p style="margin: 0; color: #6c757d; font-size: 13px;">
                <strong>Source:</strong> <a href="https://www.billboard.com/charts/india-songs-hotw/" style="color: #d41367; text-decoration: none;">Billboard India Songs - Hot This Week</a>
            </p>
            <p style="margin: 8px 0 0 0; color: #adb5bd; font-size: 12px;">
                Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")} • Click the icons next to song titles to search
            </p>
        </div>
    </div>
    """
    
    return html

def send_email(songs_data):
    """
    Send email with the chart data using environment variables for credentials
    """
    # Get credentials from environment variables (GitHub Secrets)
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not all([sender_email, sender_password, recipient_email]):
        print("❌ Error: Missing email configuration. Please check GitHub Secrets.")
        print(f"   SENDER_EMAIL: {'✅' if sender_email else '❌'}")
        print(f"   SENDER_PASSWORD: {'✅' if sender_password else '❌'}")
        print(f"   RECIPIENT_EMAIL: {'✅' if recipient_email else '❌'}")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"🎵 Billboard India Hot Songs - Top {len(songs_data)} ({datetime.now().strftime('%B %d, %Y')})"
        
        # Create HTML content only (no text version)
        html_content = create_html_table(songs_data)
        
        # Attach HTML part only
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        print(f"📧 Connecting to {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}!")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    """
    Main function to run the scraper and send email
    """
    print("🎵 Starting Billboard India chart scraper...")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("🌐 Fetching data from: https://www.billboard.com/charts/india-songs-hotw/")
    
    # Scrape the chart
    songs_data = scrape_billboard_india()
    
    if songs_data:
        print(f"✅ Successfully scraped {len(songs_data)} songs")
        
        # Display top 10 in console for verification
        print(f"\n🔥 Top 10 Songs This Week:")
        print("-" * 60)
        for song in songs_data[:10]:
            print(f"{song['Position']:2d}. {song['Song'][:40]:<40} - {song['Artist'][:20]}")
        
        if len(songs_data) > 10:
            print(f"... and {len(songs_data) - 10} more songs")
        
        # Send email
        print(f"\n📧 Sending email with {len(songs_data)} songs...")
        if send_email(songs_data):
            print("✅ Billboard India chart sent successfully!")
        else:
            print("❌ Failed to send email.")
            exit(1)
    else:
        print("❌ No data scraped. The website structure may have changed.")
        print("🔍 Please check the Billboard India URL or update the scraping logic.")
        exit(1)

if __name__ == "__main__":
    main()
