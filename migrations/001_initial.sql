CREATE TABLE players (
 id TEXT PRIMARY KEY,
 username TEXT NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9_]{3,24}$'),
 display_name TEXT NOT NULL CHECK (length(display_name) BETWEEN 2 AND 24),
 password_hash TEXT NOT NULL,
 created_at BIGINT NOT NULL
);
CREATE TABLE challenges (
 id TEXT PRIMARY KEY,
 day DATE NOT NULL,
 game TEXT NOT NULL CHECK (game IN ('lights','slide','memory','flood')),
 difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','tricky')),
 puzzle JSONB NOT NULL,
 created_at BIGINT NOT NULL,
 UNIQUE(day,game,difficulty)
);
CREATE TABLE attempts (
 id TEXT PRIMARY KEY,
 player_id TEXT NOT NULL REFERENCES players(id),
 challenge_id TEXT NOT NULL REFERENCES challenges(id),
 state JSONB NOT NULL,
 revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
 last_index INTEGER,
 started_at BIGINT NOT NULL,
 finished_at BIGINT,
 moves INTEGER NOT NULL DEFAULT 0 CHECK (moves >= 0),
 elapsed_ms BIGINT,
 UNIQUE(player_id,challenge_id)
);
CREATE INDEX idx_attempts_rank ON attempts(challenge_id,moves,elapsed_ms) WHERE finished_at IS NOT NULL;
CREATE TABLE auth_limits (
 key TEXT PRIMARY KEY,
 window_start BIGINT NOT NULL,
 count INTEGER NOT NULL
);
