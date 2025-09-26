import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
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
        
        # Find chart entries - Billboard uses specific classes for chart items
        chart_items = soup.find_all('div', class_='o-chart-results-list__item')
        
        if not chart_items:
            # Try alternative selectors if the main one doesn't work
            chart_items = soup.find_all('li', class_='lrv-u-width-100p')
        
        songs_data = []
        
        for i, item in enumerate(chart_items[:20]):  # Get top 20
            try:
                # Extract position
                position = i + 1
                
                # Extract song title - try multiple selectors
                title_elem = (item.find('h3', class_='c-title') or 
                             item.find('h3') or 
                             item.find('span', class_='chart-element__information__song'))
                title = title_elem.get_text().strip() if title_elem else "N/A"
                
                # Extract artist - try multiple selectors
                artist_elem = (item.find('span', class_='c-label') or 
                              item.find('p', class_='c-tagline') or
                              item.find('span', class_='chart-element__information__artist'))
                artist = artist_elem.get_text().strip() if artist_elem else "N/A"
                
                # Extract last week position if available
                last_week_elem = item.find('span', class_='chart-element__meta__last-week')
                last_week = last_week_elem.get_text().strip() if last_week_elem else "NEW"
                
                # Clean up the data
                title = title.replace('\n', ' ').replace('\t', ' ').strip()
                artist = artist.replace('\n', ' ').replace('\t', ' ').strip()
                
                songs_data.append({
                    'Position': position,
                    'Song': title,
                    'Artist': artist,
                    'Last Week': last_week
                })
                
                print(f"Scraped: {position}. {title} - {artist}")
                
            except Exception as e:
                print(f"Error extracting data for item {i+1}: {e}")
                continue
        
        print(f"Successfully scraped {len(songs_data)} songs")
        return songs_data
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []

def create_html_table(songs_data):
    """
    Create an HTML table from the songs data
    """
    if not songs_data:
        return "<p>No chart data available. The website structure may have changed.</p>"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #d41367; text-align: center;">🎵 Billboard India Songs - Hot This Week (Top 20)</h2>
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
        print("Error: Missing email configuration. Please check GitHub Secrets.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"🎵 Billboard India Hot Songs - Top 20 ({datetime.now().strftime('%B %d, %Y')})"
        
        # Create HTML content
        html_content = create_html_table(songs_data)
        
        # Create plain text version
        text_content = f"Billboard India Songs - Hot This Week (Top 20)\nChart Date: {datetime.now().strftime('%B %d, %Y')}\n\n"
        text_content += "-" * 60 + "\n"
        
        for song in songs_data:
            text_content += f"{song['Position']:2d}. {song['Song']} - {song['Artist']}"
            if song['Last Week'] != 'N/A':
                text_content += f" (Last Week: {song['Last Week']})"
            text_content += "\n"
        
        text_content += "-" * 60 + "\n"
        text_content += f"Data scraped from Billboard.com\nGenerated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        print(f"Connecting to {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"📧 Email sent successfully to {recipient_email}!")
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
    
    # Scrape the chart
    songs_data = scrape_billboard_india()
    
    if songs_data:
        print(f"✅ Successfully scraped {len(songs_data)} songs")
        
        # Display top 10 in console
        print("\n🔥 Top 10 Songs This Week:")
        print("-" * 50)
        for song in songs_data[:10]:
            print(f"{song['Position']:2d}. {song['Song']} - {song['Artist']}")
        
        if len(songs_data) > 10:
            print(f"... and {len(songs_data) - 10} more songs")
        
        # Send email
        print("\n📧 Sending email...")
        if send_email(songs_data):
            print("✅ Billboard India chart sent successfully!")
        else:
            print("❌ Failed to send email.")
            exit(1)
    else:
        print("❌ No data scraped. Please check the website structure or network connection.")
        exit(1)

if __name__ == "__main__":
    main()
