# plex-watchlist-analyser

A small Streamlit app to collect and visualise Plex watchlist RSS feed entries for friends.

## What it does

- Reads one or more Plex Watchlist RSS feeds and stores entries in a local SQLite database (`plex_vault.db`).
- Provides a Streamlit UI to view collected items, manage known friends (map Plex IDs to friendly names), and manage RSS feed configuration.
- Adds a "Diagrams" tab with two visualisations:
	- Requests per User: bar chart showing how many items each friend has added to their watchlist.
	- Requests over Time: time-series showing number of requests aggregated by day, week, or month.

## Requirements

This project uses Python 3.8+ and the libraries listed in `requirements.txt`.

Minimum dependencies (already in `requirements.txt`):

- streamlit
- feedparser
- pandas

Install them with:

```bash
pip install -r requirements.txt
```

## Running

Start the Streamlit app:

```bash
streamlit run plex-manager.py
```

The app will open in your browser (usually at http://localhost:8501). Use the UI tabs to:

- Dashboard — view recent watchlist items and sync all configured feeds.
- Diagrams — view the new visualisations (requests per user, requests over time).
- Friends — map Plex author IDs to friendly names.
- Feed Management — add/remove the RSS feed URLs used to populate the database.

![Plex Watchlist Analyser — Dashboard](screenshots/dashboard.png)

## Contributing

Feel free to open issues or PRs. If you change the schema, update the `init_db()` function in `plex-manager.py` to migrate/create tables accordingly.
