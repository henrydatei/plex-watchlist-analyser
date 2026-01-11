import feedparser
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "plex_vault.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS feeds (url TEXT PRIMARY KEY, label TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (author_id TEXT PRIMARY KEY, friendly_name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist 
                 (author_id TEXT, title TEXT, link TEXT, img_url TEXT, pub_date TIMESTAMP,
                  UNIQUE(author_id, link))''')
    conn.commit()
    conn.close()

def get_feeds():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM feeds", conn)
    conn.close()
    return df

def update_all_feeds():
    feeds_df = get_feeds()
    if feeds_df.empty:
        return 0
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    new_items_total = 0
    
    for _, row in feeds_df.iterrows():
        feed = feedparser.parse(row['url'])
        for entry in feed.entries:
            aid = entry.get('author', 'Unknown')
            title = entry.get('title', 'Unknown')
            link = entry.get('link', '')
            img = entry.get('media_thumbnail', [{'url': ''}])[0]['url']
            
            try:
                dt = datetime(*entry.published_parsed[:6])
            except:
                dt = datetime.now()

            c.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (aid, f"New: {aid[:6]}"))
            c.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?, ?, ?, ?)", (aid, title, link, img, dt))
            if c.rowcount > 0:
                new_items_total += 1
                
    conn.commit()
    conn.close()
    return new_items_total
