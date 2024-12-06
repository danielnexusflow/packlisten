from pydantic import BaseModel
from typing import List, Optional

class BoxModel(BaseModel):
    width: int
    depth: int
    height: int
    weight: float
    quantity: int
    shape: str = 'rectangular'
    can_rotate: bool = True
    type_id: Optional[int] = None
    overage: int = 0

class PalletModel(BaseModel):
    width: int
    depth: int
    height: int
    own_weight: float
    max_weight: float
    type_id: int
