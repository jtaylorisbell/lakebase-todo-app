-- Lakebase DDL for Todo App
-- Run this against your Lakebase PostgreSQL instance

-- Drop existing objects if they exist (for clean re-deployment)
DROP TABLE IF EXISTS todos;

-- Todos table
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    completed BOOLEAN NOT NULL DEFAULT false,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    user_email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_todos_user_email ON todos (user_email);
CREATE INDEX idx_todos_completed ON todos (completed);
CREATE INDEX idx_todos_created_at ON todos (created_at DESC);
CREATE INDEX idx_todos_priority ON todos (priority);

-- Grant permissions on sequences for Databricks Apps service principals
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO PUBLIC;
