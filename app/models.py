from pydantic import BaseModel
from typing import List, Optional

class BoxModel(BaseModel):
    width: int
    depth: int
    height: int
    weight: int
    quantity: int
    shape: str = 'rectangular'
    can_rotate: bool = True
    type_id: Optional[int] = None
    overage: int = 0

class PalletModel(BaseModel):
    width: int
    depth: int
    height: int
    own_weight: int
    max_weight: int
    type_id: int
