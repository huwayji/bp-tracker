import sqlite3
import csv
import os


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blood_pressure.db')
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sys INTEGER NOT NULL,
                dia INTEGER NOT NULL,
                heart_rate INTEGER NOT NULL,
                notes TEXT DEFAULT ''
            )
        ''')
        self.conn.commit()

    def add_reading(self, timestamp, sys, dia, heart_rate, notes=''):
        self.cursor.execute(
            'INSERT INTO readings (timestamp, sys, dia, heart_rate, notes) VALUES (?, ?, ?, ?, ?)',
            (timestamp, sys, dia, heart_rate, notes)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_readings(self):
        self.cursor.execute('SELECT * FROM readings ORDER BY timestamp DESC')
        return self.cursor.fetchall()

    def get_reading(self, reading_id):
        self.cursor.execute('SELECT * FROM readings WHERE id = ?', (reading_id,))
        return self.cursor.fetchone()

    def update_reading(self, reading_id, timestamp, sys, dia, heart_rate, notes=''):
        self.cursor.execute(
            'UPDATE readings SET timestamp=?, sys=?, dia=?, heart_rate=?, notes=? WHERE id=?',
            (timestamp, sys, dia, heart_rate, notes, reading_id)
        )
        self.conn.commit()

    def delete_reading(self, reading_id):
        self.cursor.execute('DELETE FROM readings WHERE id = ?', (reading_id,))
        self.conn.commit()

    def get_statistics(self):
        self.cursor.execute('''
            SELECT
                COUNT(*),
                ROUND(AVG(sys), 1),
                ROUND(AVG(dia), 1),
                ROUND(AVG(heart_rate), 1),
                MAX(sys),
                MIN(sys),
                MAX(dia),
                MIN(dia)
            FROM readings
        ''')
        return self.cursor.fetchone()

    def get_latest_reading(self):
        self.cursor.execute('SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1')
        return self.cursor.fetchone()

    def delete_all(self):
        self.cursor.execute('DELETE FROM readings')
        self.conn.commit()

    def export_csv(self, filepath):
        rows = self.get_all_readings()
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Timestamp', 'SYS', 'DIA', 'Heart Rate', 'Notes'])
            for row in rows:
                writer.writerow(row)
        return filepath

    def close(self):
        self.conn.close()
