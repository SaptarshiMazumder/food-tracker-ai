import os
import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class PartialStore:
    """Minimal DynamoDB-backed partial store for streaming phases.

    Table schema (provision this once):
      - TableName: FOOD_ANALYZER_PARTIALS (configurable via env PARTIALS_TABLE)
      - Partition key: job_id (S)
    Item shape:
      {
        job_id: str,
        flags: { recognize: bool, ing_quant: bool, calories: bool, done: bool },
        last_phase: str,
        data: object (merged payload snapshot)
      }
    """

    def __init__(self) -> None:
        table_name = os.getenv("PARTIALS_TABLE", "FOOD_ANALYZER_PARTIALS")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-1"
        self._table_name = table_name
        self._client = boto3.client("dynamodb", region_name=region)

    def put_phase(self, job_id: str, phase: str, payload: Dict[str, Any]) -> None:
        try:
            # Read existing to merge
            existing = self.get_status(job_id) or {}
            flags = existing.get("flags") or {}
            flags[phase] = True
            merged = existing.get("data") or {}
            merged.update(payload or {})
            item = {
                "job_id": {"S": job_id},
                "flags": {"S": json.dumps(flags)},
                "last_phase": {"S": phase},
                "data": {"S": json.dumps(merged, ensure_ascii=False)},
            }
            self._client.put_item(TableName=self._table_name, Item=item)
        except (BotoCoreError, ClientError):
            pass

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = self._client.get_item(TableName=self._table_name, Key={"job_id": {"S": job_id}})
            item = res.get("Item")
            if not item:
                return None
            flags = json.loads(item.get("flags", {}).get("S", "{}") or "{}")
            data = json.loads(item.get("data", {}).get("S", "{}") or "{}")
            last_phase = item.get("last_phase", {}).get("S")
            data["flags"] = flags
            if last_phase:
                data["last_phase"] = last_phase
            return data
        except (BotoCoreError, ClientError):
            return None


