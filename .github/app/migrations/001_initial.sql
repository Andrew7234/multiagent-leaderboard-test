-- Migration: 001_initial
-- Description: Create leaderboards and submissions tables

CREATE TABLE IF NOT EXISTS leaderboards (
    id SERIAL PRIMARY KEY,
    github_repo_id BIGINT UNIQUE NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    installation_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leaderboards_repo_full_name ON leaderboards(repo_full_name);

CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    workflow_run_id BIGINT UNIQUE NOT NULL,
    leaderboard_repo VARCHAR(255) NOT NULL,
    purple_repo VARCHAR(255) NOT NULL,
    purple_owner VARCHAR(255) NOT NULL,
    pr_number INTEGER,
    pr_url VARCHAR(500),
    results_json JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_leaderboard_repo ON submissions(leaderboard_repo);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
