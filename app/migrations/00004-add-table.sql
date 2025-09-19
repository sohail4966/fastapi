--add column exec_plan in tech_indi table

ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS exec_plan JSON;
