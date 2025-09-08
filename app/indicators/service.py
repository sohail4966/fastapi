#  all business logic related to indicators

import json
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, logger
from app.indicators.repo import IndicatorBase, IndicatorCreate, IndicatorUpdate


class IndicatorService:
    TABLE = 'technical_indicators'

    def __init__(self, client=None):
        self.client = client 


    def _row_from_model(self, model: IndicatorBase, id: Optional[str] = None):
        """
        Generate a row of data from a given model object for storage in a database.
        @param model - The IndicatorBase model object
        @param id - Optional ID for the row, if not provided, a new UUID will be generated
        @return A dictionary representing a row of data for the model
        """
        _id = id or str(uuid.uuid4())
        return {
        'id': _id,
        'indicator_name': model.indicator_name,
        'category': model.category or '',
        'description': model.description or '',
        'formula': model.formula,
        'dependencies': json.dumps(model.dependencies, ensure_ascii=False),
        'parameters': json.dumps(model.parameters, ensure_ascii=False),
        }
    

    def create_indicator(self, payload: IndicatorCreate) -> str:
        """
        Create a new indicator based on the provided payload.
        @param payload - The payload containing information about the new indicator.
        @return The ID of the newly created indicator.
        """
        # ensure unique indicator_name
        q = f"SELECT id FROM {self.TABLE} WHERE indicator_name = %(name)s LIMIT 1"
        rows = self.client.query(q, parameters={'name': payload.indicator_name}).result_rows
        if rows:
            raise HTTPException(status_code=409, detail="indicator_name already exists")

        row = self._row_from_model(payload)

        self.client.insert(self.TABLE, [(
        row['id'], row['indicator_name'], row['category'], row['description'], row['formula'], row['dependencies'], row['parameters']
        )], column_names=['id','indicator_name','category','description','formula','dependencies','parameters'])
        return row['id']


    def update_indicator(self, id: str, payload: IndicatorUpdate) -> bool:
        """
        Update an indicator with new information.
        @param id - The identifier of the indicator to update.
        @param payload - The new information to update the indicator with.
        @return True if the update was successful, False otherwise.
        """
        existing = self.get_indicator(id)
        if not existing:
            return False

        merged = {**existing}
        for k, v in payload.model_dump(exclude_unset=True).items():
            if k in ('dependencies','parameters') and v is not None:
                 merged[k] = v
            elif v is not None:
                merged[k] = v

        row = {
            'id': merged['id'],
            'indicator_name': merged['indicator_name'],
            'category': merged.get('category',''),
            'description': merged.get('description',''),
            'formula': merged.get('formula',''),
            'dependencies': json.dumps(merged.get('dependencies',{}), ensure_ascii=False),
            'parameters': json.dumps(merged.get('parameters',{}), ensure_ascii=False),
            }
        self.client.insert(self.TABLE, [(
                row['id'], row['indicator_name'], row['category'], 
                row['description'],row['formula'], row['dependencies'], row['parameters'])], 
                column_names=['id','indicator_name','category','description','formula','dependencies','parameters'])
        return True


    def get_indicator(self, id_or_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an indicator from the database based on the provided ID or name.
        @param id_or_name - The ID or name of the indicator to retrieve.
        @return A dictionary containing the indicator's details such as ID, name, category, description, formula, dependencies, parameters, creation and update timestamps. If the indicator is not found, return None.
        """
        sel = f"""
            SELECT id, indicator_name, category, description, formula,
                dependencies, parameters, created_at, updated_at
            FROM {self.TABLE}
            WHERE id = %(id)s OR indicator_name = %(name)s
            LIMIT 1
        """
        res = self.client.query(sel, params={'id': id_or_name, 'name': id_or_name})
        if not res.result_rows:
            return None
        r = res.result_rows[0]
        return {
            'id': r[0],
            'indicator_name': r[1],
            'category': r[2],
            'description': r[3],
            'formula': r[4],
            'dependencies': json.loads(r[5]) if r[5] else {},
            'parameters': json.loads(r[6]) if r[6] else {},
            'created_at': str(r[7]) if r[7] else None,
            'updated_at': str(r[8]) if r[8] else None,
        }

    def list_indicators(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List indicators from the database with optional limit and offset parameters.
        @param self - the instance of the class
        @param limit - the maximum number of indicators to retrieve (default is 100)
        @param offset - the offset from where to start retrieving indicators (default is 0)
        @return a list of dictionaries containing indicator information
        """
        sel = f"SELECT id, indicator_name, category, description, formula, dependencies, parameters, created_at, updated_at FROM {self.TABLE} ORDER BY indicator_name LIMIT %(limit)s OFFSET %(offset)s"
        res = self.client.query(sel, parameters={'limit': limit, 'offset': offset})
        out = []
        for r in res.result_rows:
            out.append({
            'id': f'{r[0]}',
            'indicator_name': r[1],
            'category': r[2],
            'description': r[3],
            'formula': r[4],
            'dependencies': r[5],
            'parameters': r[6],
            'created_at': str(r[7]) if r[7] else None,
            'updated_at': str(r[8]) if r[8] else None,
            })
        return out


    def delete_indicator(self, id: str) -> bool:
        """
        Delete an entry from a table based on the provided ID.
        @param id - The ID of the entry to be deleted.
        @return True if the deletion was successful, False otherwise.
        """
        try:
            self.client.command(f"ALTER TABLE {self.TABLE} DELETE WHERE id = '{id}'")
            return True
        except Exception as ex:
            logger.error(f"Failed to delete indicator {id}: {ex}")
            return False