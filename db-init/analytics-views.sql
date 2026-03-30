-- Analytics views for Metabase / Looker Studio
-- Run: docker exec ce-agents-postgres-1 psql -U ce -d ce_platform -f /tmp/views.sql

-- View 1: Run analytics with flattened fields
CREATE OR REPLACE VIEW v_run_analytics AS
SELECT
    r.id AS run_id,
    r.protocol_key,
    CASE
        WHEN r.protocol_key LIKE 'p0%' THEN 'core'
        WHEN r.protocol_key LIKE 'p1%' THEN 'intelligence'
        WHEN r.protocol_key LIKE 'p2%' THEN 'creative'
        WHEN r.protocol_key LIKE 'p3%' THEN 'systems_thinking'
        WHEN r.protocol_key LIKE 'p4%' THEN 'meta'
        ELSE 'other'
    END AS protocol_category,
    r.question,
    r.source,
    r.status,
    r.result_summary,
    r.error_message,
    r.total_cost_usd,
    r.total_input_tokens,
    r.total_output_tokens,
    r.total_input_tokens + r.total_output_tokens AS total_tokens,
    jsonb_array_length(r.agent_keys) AS num_agents,
    (SELECT string_agg(ak.value #>> '{}', ', ')
     FROM jsonb_array_elements(r.agent_keys) ak) AS agent_list,
    r.started_at,
    r.completed_at,
    EXTRACT(EPOCH FROM (r.completed_at - r.started_at)) AS duration_seconds,
    r.created_at,
    r.langfuse_trace_id,
    r.result_json->>'synthesis' AS synthesis_text,
    CASE
        WHEN r.result_json->'steps' IS NOT NULL
        THEN jsonb_array_length(r.result_json->'steps')
    END AS num_steps,
    CASE
        WHEN r.result_json->'rounds' IS NOT NULL
        THEN jsonb_array_length(r.result_json->'rounds')
    END AS num_rounds,
    CASE
        WHEN r.result_json->'warnings' IS NOT NULL
        THEN jsonb_array_length(r.result_json->'warnings')
        ELSE 0
    END AS num_warnings
FROM runs r;

-- View 2: Per-agent performance across runs
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    ao.agent_key,
    ao.run_id,
    r.protocol_key,
    r.question,
    ao.round_number,
    ao.model,
    ao.cost_usd,
    ao.input_tokens,
    ao.output_tokens,
    ao.input_tokens + ao.output_tokens AS total_tokens,
    LENGTH(ao.output_text) AS output_length_chars,
    ao.started_at,
    ao.completed_at,
    EXTRACT(EPOCH FROM (ao.completed_at - ao.started_at)) AS duration_seconds,
    CASE WHEN (ao.input_tokens + ao.output_tokens) > 0
         THEN ao.cost_usd / (ao.input_tokens + ao.output_tokens)
    END AS cost_per_token
FROM agent_outputs ao
JOIN runs r ON r.id = ao.run_id;

-- View 3: Protocol-level summary stats
CREATE OR REPLACE VIEW v_protocol_summary AS
SELECT
    r.protocol_key,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE r.status = 'completed') AS completed_runs,
    COUNT(*) FILTER (WHERE r.status = 'failed') AS failed_runs,
    ROUND(AVG(r.total_cost_usd)::numeric, 4) AS avg_cost_usd,
    ROUND(SUM(r.total_cost_usd)::numeric, 4) AS total_cost_usd,
    ROUND(AVG(r.total_input_tokens + r.total_output_tokens)::numeric, 0) AS avg_total_tokens,
    ROUND(AVG(EXTRACT(EPOCH FROM (r.completed_at - r.started_at)))::numeric, 1) AS avg_duration_seconds,
    ROUND(AVG(jsonb_array_length(r.agent_keys))::numeric, 1) AS avg_num_agents,
    MIN(r.created_at) AS first_run,
    MAX(r.created_at) AS last_run
FROM runs r
GROUP BY r.protocol_key;

-- View 4: Daily cost/usage dashboard
CREATE OR REPLACE VIEW v_daily_usage AS
SELECT
    DATE(r.created_at) AS run_date,
    COUNT(*) AS num_runs,
    COUNT(DISTINCT r.protocol_key) AS distinct_protocols,
    ROUND(SUM(r.total_cost_usd)::numeric, 4) AS total_cost_usd,
    SUM(r.total_input_tokens) AS total_input_tokens,
    SUM(r.total_output_tokens) AS total_output_tokens,
    SUM(r.total_input_tokens + r.total_output_tokens) AS total_tokens
FROM runs r
GROUP BY DATE(r.created_at)
ORDER BY run_date;
