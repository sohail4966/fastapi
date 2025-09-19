from typing import List
from app.indicators.eval_engine import safe_eval, validate_expr
from app.indicators.repo import IndicatorBase
from app.models import OHLCVData
import re
import pandas as pd

class ComputeEngine:

    def execute_indicator(self,definition: dict, df, registry: dict, params: dict = None):
        """
        Execute indicator using exec_plan from DB.
        df: pandas.DataFrame with open_price, high_price, low_price, close_price, volume
        registry: preloaded function registry (request.app.state.func_registry)
        params: runtime overrides
        """
        exec_plan = definition.get("exec_plan", {})
        if not exec_plan:
            raise ValueError("Indicator missing exec_plan")
        
        env = {
            "open_price": df["open_price"],
            "high_price": df["high_price"],
            "low_price": df["low_price"],
            "close_price": df["close_price"],
            "volume": df["volume"],
        }

        merged_params = {**(definition.get("parameters") or {}), **(params or {})}
        env.update(merged_params)
        for key, val in definition.get("parameters", {}).items():
            env[key] = val

        if any(v is None for v in env.values()):
            raise ValueError(f"Environment has None values before evaluating {step['name']}")
        steps = exec_plan.get("steps", [])
        for step in steps:
            name, expr = step["name"], step["expr"]
            validate_expr(expr, registry, list(env.keys()))
            env[name] = safe_eval(expr, env, registry)

        formula = exec_plan["formula"]
        validate_expr(formula, registry, list(env.keys()))
        return safe_eval(formula, env, registry)
    


    def parse_timeframe(self,tf: str) -> str:
        """
        Convert timeframe strings (1m, 5m, 1h, 1d, 1w, 1M) to pandas resample rules.
        """
        match = re.match(r"^(\d+)([mhdwM])$", tf)
        if not match:
            raise ValueError(f"Invalid timeframe: {tf}")

        num, unit = match.groups()
        unit_map = {
            "m": "min",
            "h": "H",
            "d": "D",
            "w": "W",
            "M": "M"  # monthly
        }
        return f"{num}{unit_map[unit]}"

    def resample_ohlcv(self,df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample OHLCV data dynamically based on timeframe string.
        """
        rule = self.parse_timeframe(timeframe)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")

        ohlcv = df.resample(rule).agg({
            "open_price": "first",
            "high_price": "max",
            "low_price": "min",
            "close_price": "last",
            "volume": "sum"
        }).dropna()

        ohlcv.reset_index(inplace=True)
        ohlcv.rename(columns={"index": "timestamp"}, inplace=True)
        return ohlcv


            


                



            