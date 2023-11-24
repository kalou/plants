import sqlite3
import time


class InMemoryHistory:
    """Local object, remembers past events and provides accounting.

    add() increments total, adding it to history.
    forget_up_to() is called to cleanup state.
    total_up_to() provides sum of recent events."""

    def __init__(self):
        self.events = {}

    def add(self, v):
        self.events[time.time()] = v

    def forget_up_to(self, interval):
        """Forget events that are no longer relevant"""
        self.events = dict(
            (k, v) for k, v in self.events.items() if k >= time.time() - interval
        )

    def total_up_to(self, interval):
        """Return sums that happened up to that far in the past"""
        return sum(v for k, v in self.events.items() if k >= time.time() - interval)


class SqliteHistory(InMemoryHistory):
    """The same as above, persisting to sqlite. Because sqlite
    defaults, only creator thread should mutate, which is fine
    given this has to be synchronized with accessing GPIO."""

    def __init__(self, name, conn):
        # pylint: disable=super-init-not-called
        self.name = name
        self.conn = conn
        cur = self.conn.cursor()
        res = cur.execute(
            'SELECT strftime("%s", ts), value FROM history WHERE name=?', [name]
        )
        self.events = dict((int(ts), int(v)) for ts, v in res.fetchall())

    def forget_up_to(self, interval):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM history WHERE name=? and ts<current_timestamp - ?",
            [self.name, interval],
        )
        self.conn.commit()
        super().forget_up_to(interval)

    def add(self, v):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO history (name, value) VALUES(?, ?)", [self.name, v])
        self.conn.commit()
        super().add(v)


class HistoryManager:
    """Factory for the above, based on config."""

    def __init__(self, config):
        db = config.get("pumps_history_db")
        if db:
            self.conn = sqlite3.connect(db)
            self.maybe_create_table(self.conn)
        else:
            self.conn = None

    def maybe_create_table(self, conn):
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS "
            "history(name, ts default CURRENT_TIMESTAMP, value)"
        )

    def history_for(self, obj):
        name = repr(obj)
        if self.conn:
            return SqliteHistory(name, self.conn)
        return InMemoryHistory()
