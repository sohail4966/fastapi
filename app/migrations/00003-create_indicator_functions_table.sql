-- Create table to store available functions for indicator expressions

CREATE TABLE IF NOT EXISTS indicator_functions (
    name LowCardinality(String),          -- function name (e.g. "ema")
    description String,                   -- human-readable doc
    category LowCardinality(String),      -- e.g. "smoothing", "math", "oscillator"
    arity UInt8,                          -- expected number of arguments
    impl_type LowCardinality(String),     -- "python" or "sql"
    expr Nullable(String),                -- optional SQL expression if impl_type="sql"
    created_at DateTime64(3, 'UTC') DEFAULT now64()
) ENGINE = MergeTree()
ORDER BY (name);
