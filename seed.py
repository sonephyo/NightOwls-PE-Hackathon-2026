import csv

from peewee import chunked

from app import create_app
from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from load_seed import load_csv


def _load_urls(filepath):
    """Load urls.csv with is_active converted from string to bool."""
    with open(filepath, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["is_active"] = row["is_active"].strip().lower() == "true"
    with db.atomic():
        for batch in chunked(rows, 100):
            Url.insert_many(batch).execute()


def seed():
    app = create_app()
    with app.app_context():
        db.create_tables([User, Url, Event], safe=True)
        if User.select().count() == 0:
            print("Seeding database...")
            load_csv("data/users.csv", User)
            _load_urls("data/urls.csv")
            load_csv("data/events.csv", Event)
            # Reset sequences so auto-increment works after bulk CSV insert
            db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
            db.execute_sql("SELECT setval('urls_id_seq', (SELECT MAX(id) FROM urls))")
            db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events))")
            print("Seed complete.")
        else:
            print("Database already seeded, skipping.")


if __name__ == "__main__":
    seed()
