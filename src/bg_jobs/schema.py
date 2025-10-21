from pydantic import BaseModel

from typing import Optional, Dict, List


class WebhookConfig(BaseModel):
    url: str
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, object]] = None
    events: Optional[List[str]] = None
