CREATE TABLE IF NOT EXISTS browsers (
  id TEXT PRIMARY KEY,
  last_day TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS totals (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  count INTEGER NOT NULL,
  started_on TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS count_new_browser
AFTER INSERT ON browsers
BEGIN
  INSERT INTO totals (id, count, started_on) VALUES (1, 1, NEW.last_day)
  ON CONFLICT(id) DO UPDATE SET count = count + 1;
END;

CREATE TRIGGER IF NOT EXISTS count_returning_browser
AFTER UPDATE OF last_day ON browsers
WHEN NEW.last_day > OLD.last_day
BEGIN
  UPDATE totals SET count = count + 1 WHERE id = 1;
END;
