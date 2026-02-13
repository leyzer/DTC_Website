import sqlite3

conn = sqlite3.connect('GPTLeague.db')
c = conn.cursor()

# Add systems if not exist
c.execute("INSERT OR IGNORE INTO systems (system_code, system_name, category) VALUES ('AOS', 'Age of Sigmar', 'AOS')")
c.execute("INSERT OR IGNORE INTO systems (system_code, system_name, category) VALUES ('40K', 'Warhammer 40k', '40k')")

# Add factions for AOS
system_id = c.execute("SELECT system_id FROM systems WHERE system_code = 'AOS'").fetchone()[0]
c.execute("INSERT OR IGNORE INTO factions (system_id, faction_name) VALUES (?, 'Stormcast Eternals')", (system_id,))
c.execute("INSERT OR IGNORE INTO factions (system_id, faction_name) VALUES (?, 'Nighthaunt')", (system_id,))

# Add season if not exist
c.execute("INSERT OR IGNORE INTO seasons (name, year, start_date, end_date) VALUES ('2026 League', 2026, '2026-01-01', '2026-12-31')")

conn.commit()
conn.close()
print('Seeded basic data')