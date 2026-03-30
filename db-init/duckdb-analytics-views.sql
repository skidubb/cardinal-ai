-- Analytics views for DuckDB-sourced agent memory data in Metabase
-- Prereq: run sync_duckdb_to_postgres.py to populate duckdb_* tables
-- Run: docker exec ce-agents-postgres-1 psql -U ce -d ce_platform -f /tmp/duckdb-views.sql

-- View 1: Agent learning — experience logs with context
CREATE OR REPLACE VIEW v_agent_learning AS
SELECT
    el.id,
    el.role AS agent_role,
    el.lesson,
    el.timestamp AS learned_at,
    (SELECT COUNT(*) FROM duckdb_experience_logs el2 WHERE el2.role = el.role) AS total_lessons_for_role,
    LENGTH(el.lesson) AS lesson_length_chars
FROM duckdb_experience_logs el
ORDER BY el.timestamp DESC;

-- View 2: Session activity — usage patterns, message counts, fork chains
CREATE OR REPLACE VIEW v_session_activity AS
SELECT
    s.id AS session_id,
    s.agent_role,
    s.title,
    s.parent_session_id,
    CASE WHEN s.parent_session_id IS NOT NULL THEN true ELSE false END AS is_forked,
    s.created_at,
    s.updated_at,
    (SELECT COUNT(*) FROM duckdb_messages m WHERE m.session_id = s.id) AS message_count,
    (SELECT COUNT(*) FROM duckdb_messages m WHERE m.session_id = s.id AND m.role = 'user') AS user_messages,
    (SELECT COUNT(*) FROM duckdb_messages m WHERE m.session_id = s.id AND m.role = 'assistant') AS assistant_messages,
    (SELECT COUNT(*) FROM duckdb_sessions child WHERE child.parent_session_id = s.id) AS fork_count
FROM duckdb_sessions s
ORDER BY s.updated_at DESC;

-- View 3: Debate overview — debate sessions with round/agent details
CREATE OR REPLACE VIEW v_debate_overview AS
SELECT
    d.id AS debate_id,
    d.question,
    d.total_rounds,
    d.status,
    d.synthesis IS NOT NULL AS has_synthesis,
    LENGTH(d.synthesis) AS synthesis_length_chars,
    d.created_at,
    d.updated_at
FROM duckdb_debate_sessions d
ORDER BY d.updated_at DESC;

-- View 4: Evaluation run summary — cost and performance tracking
CREATE OR REPLACE VIEW v_eval_run_summary AS
SELECT
    er.id AS eval_id,
    er.question_id,
    er.mode,
    er.cost,
    er.duration_seconds,
    er.created_at,
    CASE WHEN er.cost > 0 AND er.duration_seconds > 0
         THEN ROUND((er.cost / er.duration_seconds * 60)::numeric, 4)
    END AS cost_per_minute
FROM duckdb_evaluation_runs er
ORDER BY er.created_at DESC;

-- View 5: Agent learning rate — lessons per role over time
CREATE OR REPLACE VIEW v_agent_learning_rate AS
SELECT
    role AS agent_role,
    COUNT(*) AS total_lessons,
    MIN(timestamp) AS first_lesson,
    MAX(timestamp) AS latest_lesson,
    ROUND(AVG(LENGTH(lesson))::numeric, 0) AS avg_lesson_length
FROM duckdb_experience_logs
GROUP BY role
ORDER BY total_lessons DESC;
