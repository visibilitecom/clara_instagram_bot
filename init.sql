CREATE TABLE IF NOT EXISTS user_memory (
    user_id TEXT PRIMARY KEY,
    profile JSONB DEFAULT '{}'::jsonb,
    history JSONB DEFAULT '[]'::jsonb,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_link BOOLEAN DEFAULT FALSE
);

