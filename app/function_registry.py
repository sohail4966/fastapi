import pandas as pd
import numpy as np
from fastapi import Request, Depends
from clickhouse_connect.driver.client import Client
from app.dependency import get_db_client  # use your existing dependency

# Local implementations of functions
PYTHON_FUNCTIONS = {
    "sma": lambda s, n: s.rolling(window=int(n), min_periods=int(n)).mean(),
    "ema": lambda s, n: s.ewm(span=int(n), adjust=False).mean(),
    "wilder": lambda s, n: s.ewm(alpha=1/int(n), adjust=False, min_periods=int(n)).mean(),
    "diff": lambda s: s.diff() if isinstance(s, pd.Series) else None,
    "cumsum": lambda s: s.cumsum(),
    "max": lambda a, b: pd.Series(np.maximum(a, b), index=a.index if isinstance(a, pd.Series) else None),
    "min": lambda a, b: pd.Series(np.minimum(a, b), index=a.index if isinstance(a, pd.Series) else None),
    "abs": lambda s: s.abs(),
    "shift": lambda s, n: s.shift(int(n)),
    "rolling_max": lambda s, n: s.rolling(window=int(n), min_periods=int(n)).max(),
    "rolling_min": lambda s, n: s.rolling(window=int(n), min_periods=int(n)).min(),
    "stdev": lambda s, n: s.rolling(window=int(n), min_periods=int(n)).std(),
}

def load_function_registry(db: Client) -> dict:
    """
    Load the indicator function registry from the database.
    @param db - ClickHouse client (injected via get_db_client).
    @return dict mapping function name -> implementation.
    """
    rows = db.query(
        "SELECT name, impl_type FROM indicator_functions"
    ).result_rows

    registry = {}
    for name, impl_type in rows:
        if impl_type == "python":
            if name not in PYTHON_FUNCTIONS:
                raise ValueError(f"No Python implementation found for {name}")
            registry[name] = PYTHON_FUNCTIONS[name]
        elif impl_type == "sql":
            # Placeholder for SQL-executable functions
            registry[name] = lambda *args: f"{name}({','.join(map(str,args))})"
        else:
            raise ValueError(f"Unsupported impl_type {impl_type} for {name}")
    return registry
