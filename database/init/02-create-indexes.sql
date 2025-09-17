-- Additional indexes and optimizations for SEPE Templates Comparator
-- This script runs after Alembic migrations to add performance optimizations

\c sepe_comparator;

-- Full-text search indexes for templates
CREATE INDEX IF NOT EXISTS idx_pdf_templates_search 
ON pdf_templates USING GIN (to_tsvector('spanish', name || ' ' || COALESCE(sepe_url, '')));

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pdf_templates_user_created 
ON pdf_templates (uploaded_by, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comparisons_user_status 
ON comparisons (created_by, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comparison_fields_comparison 
ON comparison_fields (comparison_id, change_type);

-- Partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_users_active_email 
ON users (email) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_templates_recent 
ON pdf_templates (created_at DESC) 
WHERE created_at > (CURRENT_DATE - INTERVAL '30 days');

-- Index for template versions
CREATE INDEX IF NOT EXISTS idx_template_versions_current 
ON template_versions (template_id, is_current, created_at DESC);

-- Performance optimization for large comparisons
CREATE INDEX IF NOT EXISTS idx_comparisons_completed 
ON comparisons (completed_at DESC) 
WHERE status = 'completed';

-- Trigram indexes for fuzzy search
CREATE INDEX IF NOT EXISTS idx_pdf_templates_name_trgm 
ON pdf_templates USING GIN (name gin_trgm_ops);

-- Statistics update for better query planning
ANALYZE users;
ANALYZE pdf_templates;
ANALYZE template_versions;
ANALYZE comparisons;
ANALYZE comparison_fields;
