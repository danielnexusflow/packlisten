import json
import logging
from typing import List, Dict, Tuple


class Box:
    def __init__(self, width, depth, height, weight, quantity, shape='rectangular', can_rotate=True, type_id=None, overage=0):
        self.width = width
        self.depth = depth
        self.height = height
        self.weight = weight
        self.quantity = quantity
        self.shape = shape  # 'rectangular' or 'round'
        self.can_rotate = can_rotate  # If the box can be rotated
        self.id = type_id or id(self)  # Unique identifier for the box instance
        self.overage = overage  # Extra length allowed beyond the pallet's width


class Pallet:
    def __init__(self, width, depth, height, own_weight, max_weight, type_id):
        self.width = width
        self.depth = depth
        self.height = height
        self.own_weight = own_weight
        self.max_weight = max_weight
        self.type_id = type_id
        self.current_weight = 0
        self.used_space = []  # Stores placed boxes with positions and dimensions

    def can_place_box(self, x, y, z, box):
        # Check if the pallet already has 30 boxes
        if len(self.used_space) >= 30:
            logging.info('Box does not fit on pallet because it exceeds max box count of 30')
            return False
        
        # Check if box fits within the pallet dimensions considering overage
        if x + box.width > self.width + box.overage or y + box.depth > self.depth or z + box.height > self.height:
            logging.info('Box does not fit on pallet because it is too big (for the available space)')
            return False

        # Check if box exceeds weight capacity
        if self.current_weight + box.weight > self.max_weight:
            logging.info('Box does not fit on pallet because it is too heavy (for the available weight)')
            return False

        # Check for overlaps with already placed boxes
        for placed_box in self.used_space:
            if self.boxes_overlap(x, y, z, box, placed_box):
                logging.info('Box does not fit on pallet because it overlaps with another pallet.')
                return False

        return True

    def boxes_overlap(self, x1, y1, z1, box1, placed_box):
        x2, y2, z2, box2 = placed_box['position'][0], placed_box['position'][1], placed_box['position'][2], placed_box['box']

        return not (
            x1 + box1.width <= x2 or x2 + box2.width <= x1 or
            y1 + box1.depth <= y2 or y2 + box2.depth <= y1 or
            z1 + box1.height <= z2 or z2 + box2.height <= z1
        )

    def place_box(self, x, y, z, box):
        self.used_space.append({
            'position': (x, y, z),
            'box': box
        })
        self.current_weight += box.weight

    def reset(self):
        self.used_space = []
        self.current_weight = 0


def remove_duplicate_pallet_types(pallets: List[Pallet]) -> List[Pallet]:
    """
    Ensure there is only one pallet of each type in the initial list.
    """
    unique_pallets = {}
    for pallet in pallets:
        if pallet.type_id not in unique_pallets:
            unique_pallets[pallet.type_id] = pallet
    return list(unique_pallets.values())


def add_new_pallet_of_type(pallets: List[Pallet], type_id: int) -> Pallet:
    """
    Add a new pallet of a given type_id by cloning an existing one.
    """
    for pallet in pallets:
        if pallet.type_id == type_id:
            # Clone the pallet with reset weight and used space
            new_pallet = Pallet(
                width=pallet.width,
                depth=pallet.depth,
                height=pallet.height,
                own_weight=pallet.own_weight,
                max_weight=pallet.max_weight,
                type_id=pallet.type_id
            )
            return new_pallet
    raise ValueError(f"No pallet with type_id {type_id} found.")


def find_next_bigger_pallet(pallets: List[Pallet], current_pallet: Pallet) -> Pallet:
    """
    Finds the next bigger pallet based on volume and weight compared to the current pallet.
    """
    sorted_pallets = sorted(pallets, key=lambda p: (
        p.width * p.depth * p.height, p.max_weight))
    for pallet in sorted_pallets:
        if pallet.width * pallet.depth * pallet.height >= current_pallet.width * current_pallet.depth * current_pallet.height and pallet.max_weight > current_pallet.max_weight:
            return Pallet(
                width=pallet.width,
                depth=pallet.depth,
                height=pallet.height,
                own_weight=pallet.own_weight,
                max_weight=pallet.max_weight,
                type_id=pallet.type_id
            )
    return None  # No bigger pallet available


def finish_pallet(current_pallet, result):
    if current_pallet.used_space:
        pallet_items = []
        total_height = 0
        for placed_box in current_pallet.used_space:
            pallet_items.append({
                "box_id": placed_box['box'].id,
                "shape": placed_box['box'].shape,
                "weight": placed_box['box'].weight,
                "dimensions": (placed_box['box'].width, placed_box['box'].depth, placed_box['box'].height),
                "position": placed_box['position']
            })
            total_height = max(
                total_height, placed_box['position'][2] + placed_box['box'].height)

        result.append({
            "type_id": current_pallet.type_id,
            "items": pallet_items,
            "load_weight": current_pallet.current_weight,
            "total_weight": current_pallet.current_weight + current_pallet.own_weight,
            "total_height": total_height,
            "total_items": len(pallet_items)
        })


def try_to_place_box(box, pallet):
    placed = False

    orientations = [(box.width, box.depth, box.height)]
    if box.can_rotate:
        orientations.extend([
            (box.depth, box.width, box.height),
            (box.height, box.depth, box.width),
            (box.width, box.height, box.depth),
            (box.depth, box.height, box.width),
            (box.height, box.width, box.depth)
        ])
        # Remove duplicate orientations
        orientations = list(set(orientations))

    for dimensions in orientations:
        box.width, box.depth, box.height = dimensions
        for z in range(0, pallet.height - box.height + 1):
            for y in range(0, pallet.depth - box.depth + 1):
                for x in range(0, pallet.width + box.overage - box.width + 1):
                    if pallet.can_place_box(x, y, z, box):
                        pallet.place_box(x, y, z, box)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if placed:
            break

    return placed, dimensions


def bigger_or_new_pallet(pallets, current_pallet, box, result):
    # Try to find a bigger pallet
    next_bigger_pallet = find_next_bigger_pallet(pallets, current_pallet)

    # If there is a next bigger pallet, check if the box fits there
    if next_bigger_pallet:
        # Transfer boxes to next bigger pallet
        next_bigger_pallet.used_space = current_pallet.used_space
        next_bigger_pallet.current_weight = current_pallet.current_weight
        placed, _ = try_to_place_box(box, next_bigger_pallet)

        if placed:
            return placed, next_bigger_pallet
        else:
            even_bigger = bigger_or_new_pallet(
                pallets, next_bigger_pallet, box, result)

            if even_bigger:
                return even_bigger
            else:
                # Add the current pallet to the result if it contains any items
                finish_pallet(current_pallet=current_pallet, result=result)

                # No bigger pallet available, add a new one
                new_pallet = add_new_pallet_of_type(
                    pallets, pallets[0].type_id)
                pallets.append(new_pallet)

                return placed, new_pallet


def optimize_pallets_ordered(pallets: List[Pallet], boxes: List[Box]) -> List[Dict]:
    # Ensure only one palette of each type in the list
    pallets = remove_duplicate_pallet_types(pallets)

    # Expand boxes into individual instances
    box_queue = []
    for box in boxes:
        for _ in range(int(box.quantity)):
            box_queue.append(box)

    # Sort boxes by type (round first) and then by descending weight and volume
    box_queue.sort(key=lambda b: (b.shape != 'rectangular',
                   b.weight, b.width * b.depth * b.height), reverse=True)

    result = []
    current_pallet = pallets[0]

    while box_queue:
        box = box_queue.pop(0)
        placed = False

        # Count round objects already on the current pallet
        round_object_count = sum(
            1 for item in current_pallet.used_space if item['box'].shape == 'round')

        # If there are already 2 round objects, do not allow rectangular items
        if box.shape == 'rectangular' and round_object_count > 2:
            # Add the current pallet to the result and create a new one
            finish_pallet(current_pallet=current_pallet, result=result)
            logging.info(
                f'Added new pallet because a rectangular box was tried to be added to a pallet containing {round_object_count} rounds objects')
            new_pallet = add_new_pallet_of_type(pallets, pallets[0].type_id)
            pallets.append(new_pallet)
            current_pallet = new_pallet

        while not placed:
            # Try to place the box
            placed, dimensions = try_to_place_box(box, current_pallet)

            # Reset box dimensions after trying rotations
            box.width, box.depth, box.height = dimensions

            if not placed:
                bigger = bigger_or_new_pallet(
                    pallets, current_pallet, box, result
                )

                if bigger:
                    placed, current_pallet = bigger
                else:
                    # Add the current pallet to the result if it contains any items
                    finish_pallet(current_pallet=current_pallet, result=result)

                    # No bigger pallet available, add a new one
                    new_pallet = add_new_pallet_of_type(
                        pallets, pallets[0].type_id)
                    pallets.append(new_pallet)
                    current_pallet = new_pallet

    finish_pallet(current_pallet=current_pallet, result=result)

    return result


# Example Usage
pallets = [
    Pallet(120, 80, 105, own_weight=22, max_weight=478, type_id=2),
    Pallet(220, 40, 60, own_weight=11, max_weight=289, type_id=1),
    Pallet(220, 80, 105, own_weight=20, max_weight=680, type_id=3),
    Pallet(220, 80, 105, own_weight=30, max_weight=770, type_id=4)
]  # Initialize with one pallet
boxes = [
    Box(213, 16, 13, weight=4.75, quantity=10,
        shape='rectangular', type_id=4, can_rotate=False),
    # Box(212, 18, 16, weight=22, quantity=14, shape='rectangular'),
    # Box(145, 20, 20, weight=60, quantity=10, shape='round'),
    Box(230, 23, 23, weight=133, quantity=8, shape='round', overage=20)
]

placements = optimize_pallets_ordered(pallets, boxes)

output_file = "pallet_placements.json"
with open(output_file, "w") as file:
    json.dump(placements, file, indent=4)

print(f"Placements saved to {output_file}")
