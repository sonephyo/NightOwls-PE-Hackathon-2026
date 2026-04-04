from app import create_app

app = create_app()

# --- One-time DB setup (uncomment to create tables and seed data, then comment out again) ---
# from app.models import User, Url, Event
# from app.database import db
# from load_seed import load_csv
#
# db.create_tables([User, Url, Event])
# if User.select().count() == 0:
#     load_csv('users.csv', User)
#     load_csv('urls.csv', Url)
#     load_csv('events.csv', Event)
# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
