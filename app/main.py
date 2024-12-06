from fastapi import FastAPI
from app.models import PalletModel, BoxModel
from app.services import optimize_pallets_ordered, Pallet, Box
from typing import List, Dict, Tuple

app = FastAPI()

@app.post("/optimize-pallets")
def optimize_pallets(pallets: List[PalletModel], boxes: List[BoxModel]) -> Dict:
    pallets = [Pallet(**pallet.dict()) for pallet in pallets]
    boxes = [Box(**box.dict()) for box in boxes]
    placements = optimize_pallets_ordered(pallets, boxes)
    return {"placements": placements}
