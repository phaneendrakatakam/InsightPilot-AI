-- InsightPilot AI | V1 Day 2 | Read-only role

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'insightpilot_readonly'
    ) THEN
        CREATE ROLE insightpilot_readonly LOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE insightpilot_db TO insightpilot_readonly;
GRANT USAGE ON SCHEMA public TO insightpilot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO insightpilot_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO insightpilot_readonly;

ALTER ROLE insightpilot_readonly SET default_transaction_read_only = on;
ALTER ROLE insightpilot_readonly SET statement_timeout = '10s';

-- Set the password interactively after running this file:
-- psql -U postgres -d insightpilot_db
-- \password insightpilot_readonly
-- \q
