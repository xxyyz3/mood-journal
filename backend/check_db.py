import sqlite3

con = sqlite3.connect("mood_journal.db")
rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(rows)
con.close()