import sys
from pathlib import Path

# Ensure project root is on sys.path so plex_core can be imported when running
# the script from the scripts/ directory.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plex_core import init_db, update_all_feeds


def main():
    init_db()
    new = update_all_feeds()
    print(f"Sync complete: {new} new items found.")
    # return non-zero if no feeds configured to make failures visible in logs
    if new == 0:
        # still success if zero new entries but feeds exist; exit 0
        sys.exit(0)


if __name__ == '__main__':
    main()
