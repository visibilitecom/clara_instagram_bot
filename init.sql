
CREATE TABLE IF NOT EXISTS user_memory (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    profile JSONB DEFAULT '{}'::jsonb,
    history JSONB DEFAULT '[]'::jsonb,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    sent_link BOOLEAN DEFAULT FALSE
);
