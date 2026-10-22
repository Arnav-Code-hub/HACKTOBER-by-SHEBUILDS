-- Runs once, when the postgres volume is first created.
--
-- Extensions only. Every table, index and constraint comes from Alembic — a
-- schema object created here would exist locally and be missing in production,
-- which is the classic "worked on my laptop, times out in the demo" bug.

CREATE EXTENSION IF NOT EXISTS postgis;      -- geo clustering, district queries
CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector: duplicate detection
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- fuzzy text match, transliterated names
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- A separate read-only role. If the AI service ever needs analytics access it
-- gets THIS, never the API's credentials. Today it is unused by design: the AI
-- service is stateless and reaches the database only through the API.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'janmaang_readonly') THEN
    CREATE ROLE janmaang_readonly WITH LOGIN PASSWORD 'readonly';
  END IF;
END
$$;
GRANT CONNECT ON DATABASE janmaang TO janmaang_readonly;
GRANT USAGE ON SCHEMA public TO janmaang_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO janmaang_readonly;
