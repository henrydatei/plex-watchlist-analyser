import streamlit as st
import feedparser
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "plex_vault.db"

# --- DATABASE LOGIC ---
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

# --- UI SETUP ---
st.set_page_config(page_title="Plex Watchlist Vault", layout="wide")
init_db()


feeds_df = get_feeds()

if feeds_df.empty:
    st.warning("No RSS feeds configured! Please add at least one feed to get started.")
    tab_list = ["Feed Management"]
else:
    tab_list = ["Dashboard", "Diagrams", "Friends", "Feed Management"]

tabs = st.tabs(tab_list)

# --- TAB: DASHBOARD ---
if "Dashboard" in tab_list:
    dash_idx = tab_list.index("Dashboard")
    with tabs[dash_idx]:
        st.title("Watchlist Overview")
        if st.button("Sync All Feeds Now"):
            new = update_all_feeds()
            st.success(f"Sync complete! Found {new} new entries.")
            st.rerun()

        # Load data with join for names
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query('''
            SELECT w.*, u.friendly_name FROM watchlist w 
            LEFT JOIN users u ON w.author_id = u.author_id 
            ORDER BY w.pub_date DESC
        ''', conn)
        conn.close()

        if not df.empty:
            users = sorted(df['friendly_name'].unique())
            sel_users = st.sidebar.multiselect("Filter by Friend", users, default=users)
            
            f_df = df[df['friendly_name'].isin(sel_users)]
            
            cols = st.columns(5)
            for i, (_, r) in enumerate(f_df.iterrows()):
                with cols[i % 5]:
                    st.image(r['img_url'] if r['img_url'] else "https://via.placeholder.com/200", width='stretch')
                    st.write(f"**{r['title']}**")
                    st.caption(f"{r['friendly_name']} | {str(r['pub_date'])[:10]}")
                    st.markdown(f"[View on Plex]({r['link']})")
        else:
            st.info("The database is currently empty. Click 'Sync All Feeds' to fetch data.")

# --- TAB: DIAGRAMS ---
if "Diagrams" in tab_list:
    diag_idx = tab_list.index("Diagrams")
    with tabs[diag_idx]:
        st.header("Request Visualisations")

        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query('''
            SELECT w.*, u.friendly_name FROM watchlist w 
            LEFT JOIN users u ON w.author_id = u.author_id 
            ORDER BY w.pub_date DESC
        ''', conn)
        conn.close()

        if df.empty:
            st.info("No data available yet. Click 'Sync All Feeds' on the Dashboard to fetch data.")
        else:
            # Ensure datetime
            df['pub_date'] = pd.to_datetime(df['pub_date'])

            # Requests per user (simple bar chart)
            st.subheader("Requests per User")
            per_user = df.groupby('friendly_name').size().sort_values(ascending=False)
            top_n = st.slider("Show top N users", min_value=1, max_value=min(20, len(per_user)), value=min(10, len(per_user)))
            st.bar_chart(per_user.head(top_n))

            st.divider()

            # Requests over time (resample)
            st.subheader("Requests over Time")
            freq = st.selectbox("Group by", options=["Day", "Week", "Month"], index=0)
            freq_map = {"Day": "D", "Week": "W", "Month": "ME"}
            ts = df.set_index('pub_date')
            counts = ts.resample(freq_map[freq]).size()
            counts.index = counts.index.to_timestamp() if hasattr(counts.index, 'to_timestamp') else counts.index
            st.line_chart(counts)

            # Optionally show a table of aggregated values
            if st.checkbox("Show aggregated table"):
                st.dataframe(counts.rename('requests').reset_index().rename(columns={'pub_date': 'period'}))

# --- TAB: USER MANAGEMENT ---
if "Friends" in tab_list:
    idx = tab_list.index("Friends")
    with tabs[idx]:
        st.header("Manage Friends")
        st.write("Assign real names to the cryptic Plex IDs below.")
        conn = sqlite3.connect(DB_NAME)
        u_df = pd.read_sql_query("SELECT * FROM users", conn)
        edited_u = st.data_editor(u_df, width='stretch', hide_index=True)
        if st.button("Save User Names"):
            # Persist edits while preserving the primary key on `author_id`.
            # Using pandas.to_sql(..., if_exists='replace') will recreate the table
            # without the PRIMARY KEY, which lets future INSERTs create duplicate
            # user rows. Instead, write into a temp table with a PRIMARY KEY and
            # swap it in atomically.
            c = conn.cursor()
            # create a temp table with the desired schema (primary key)
            c.execute('CREATE TABLE IF NOT EXISTS users_tmp (author_id TEXT PRIMARY KEY, friendly_name TEXT)')
            c.execute('DELETE FROM users_tmp')
            for _, row in edited_u.iterrows():
                aid = row.get('author_id') if 'author_id' in row.index else None
                name = row.get('friendly_name') if 'friendly_name' in row.index else None
                if aid is None:
                    continue
                # ensure strings and avoid NaN
                aid = str(aid)
                name = '' if pd.isna(name) else str(name)
                c.execute('INSERT OR REPLACE INTO users_tmp (author_id, friendly_name) VALUES (?, ?)', (aid, name))

            # replace the old users table with the deduped one
            c.execute('DROP TABLE IF EXISTS users')
            c.execute('ALTER TABLE users_tmp RENAME TO users')
            conn.commit()
            st.success('User names updated!')
        conn.close()

# --- TAB: FEED MANAGEMENT ---
with tabs[-1]:
    st.header("Manage RSS Feeds")
    
    conn = sqlite3.connect(DB_NAME)
    current_feeds = pd.read_sql_query("SELECT * FROM feeds", conn)
    
    st.subheader("Active Feeds")
    edited_feeds = st.data_editor(current_feeds, num_rows="dynamic", width='stretch', hide_index=True, key="feed_editor")
    
    if st.button("Save Feed Configuration"):
        edited_feeds.to_sql("feeds", conn, if_exists="replace", index=False)
        st.success("Feed list updated!")
        st.rerun()
    
    st.divider()
    st.info("Tip: You can find your RSS URL in Plex under 'Watchlist' -> '...' (Menu) -> 'RSS Feed'.")
    conn.close()