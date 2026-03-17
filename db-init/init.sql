-- Create a separate database for Metabase's internal storage.
-- This only runs on first Postgres init (empty pgdata volume).
CREATE DATABASE metabase;
