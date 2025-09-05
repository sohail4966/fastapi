-- Replace technical_indicators: new metadata/catalog schema

CREATE TABLE IF NOT EXISTS db1.technical_indicators (
    id UUID DEFAULT generateUUIDv4(),               -- unique ID
    indicator_name LowCardinality(String),          -- "RSI", "MACD", "EMA"
    category LowCardinality(String),                -- "Momentum", "Trend", "Volatility"
    description String,                             -- human-readable explanation
    formula String,                                 -- expression or DSL string
    dependencies JSON,                              -- JSON describing required inputs
    parameters JSON,                                -- default parameters (e.g. {"period": 14})
    created_at DateTime64(3, 'UTC') DEFAULT now64(),
    updated_at DateTime64(3, 'UTC') DEFAULT now64()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;
