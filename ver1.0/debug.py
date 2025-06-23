import sys
import json
from contextlib import closing

# adjust this path if you run the script from a different folder
from core.database import get_db
from core.models import EmailProcessingLog


def main(db_log_id=None):
    with closing(next(get_db())) as db:
        q = db.query(EmailProcessingLog)
        if db_log_id is not None:
            q = q.filter_by(id=db_log_id)
        for entry in q.all():
            print(f"\n--- Log ID: {entry.id} ---")
            print("parsed_attachments_json:")
            print(json.dumps(entry.parsed_attachments_json or [], indent=2))


if __name__ == "__main__":
    # optionally pass a single log-ID on the command line
    log_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(log_id)
