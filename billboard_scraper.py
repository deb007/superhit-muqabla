import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
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
    Create an HTML table from the songs data
    """
    if not songs_data:
        return "<p>❌ No chart data available. The website structure may have changed.</p>"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #d41367; text-align: center;">🎵 Billboard India Songs - Hot This Week (Top {len(songs_data)})</h2>
        <p style="text-align: center; color: #666; margin-bottom: 20px;">Chart Date: {datetime.now().strftime("%B %d, %Y")}</p>
        <table border="1" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <thead style="background-color: #d41367; color: white;">
                <tr>
                    <th style="padding: 12px; text-align: center; width: 10%;">Rank</th>
                    <th style="padding: 12px; text-align: left; width: 45%;">Song</th>
                    <th style="padding: 12px; text-align: left; width: 35%;">Artist</th>
                    <th style="padding: 12px; text-align: center; width: 10%;">Last Week</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, song in enumerate(songs_data):
        row_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        position_color = "#d41367" if song['Position'] <= 3 else "#333"
        
        html += f"""
            <tr style="background-color: {row_color};">
                <td style="padding: 10px; text-align: center; font-weight: bold; color: {position_color};">{song['Position']}</td>
                <td style="padding: 10px;"><strong style="color: #333;">{song['Song']}</strong></td>
                <td style="padding: 10px; color: #666;">{song['Artist']}</td>
                <td style="padding: 10px; text-align: center; color: #888;">{song['Last Week']}</td>
            </tr>
        """
    
    html += f"""
            </tbody>
        </table>
        <p style="text-align: center; color: #888; font-size: 12px; margin-top: 20px;">
            <em>Data scraped from Billboard.com • Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</em>
        </p>
        <p style="text-align: center; color: #666; font-size: 11px;">
            <strong>Source:</strong> <a href="https://www.billboard.com/charts/india-songs-hotw/" style="color: #d41367;">Billboard India Songs - Hot This Week</a>
        </p>
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
        
        # Create HTML content
        html_content = create_html_table(songs_data)
        
        # Create plain text version
        text_content = f"🎵 Billboard India Songs - Hot This Week (Top {len(songs_data)})\n"
        text_content += f"Chart Date: {datetime.now().strftime('%B %d, %Y')}\n\n"
        text_content += "=" * 70 + "\n"
        
        for song in songs_data:
            text_content += f"{song['Position']:2d}. {song['Song']}\n"
            text_content += f"    Artist: {song['Artist']}\n"
            if song['Last Week'] != 'NEW':
                text_content += f"    Last Week: #{song['Last Week']}\n"
            else:
                text_content += f"    Last Week: NEW\n"
            text_content += "\n"
        
        text_content += "=" * 70 + "\n"
        text_content += f"Source: Billboard India Songs - Hot This Week\n"
        text_content += f"URL: https://www.billboard.com/charts/india-songs-hotw/\n"
        text_content += f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
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
