"""Data transformation pipeline with rollback support."""

import copy
from typing import Any, Callable, Dict, List, Tuple

from .transforms import normalize_names, apply_discounts, enrich_timestamps, sanitize_input
from .validators import validate_required_fields, validate_no_nulls, validate_price_range


class Pipeline:
    """Data transformation pipeline that applies transforms in sequence."""

    def __init__(self):
        self.transforms: List[Callable] = []
        self.rollback_stack: List[Tuple[Callable, Any]] = []

    def add_transform(self, transform: Callable) -> "Pipeline":
        """Add a transform function to the pipeline."""
        self.transforms.append(transform)
        return self

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through all transforms with rollback on failure.
        
        BUG: The rollback mechanism fails because transforms mutate data in-place,
        so the original data is already corrupted before rollback can restore it.
        """
        # Create deep copy for potential rollback
        original_data = copy.deepcopy(data)
        
        try:
            for transform in self.transforms:
                # Apply transform - but transforms mutate in-place!
                result = transform(data)
                
                # Store rollback info (but this is useless if data was mutated)
                self.rollback_stack.append((transform, copy.deepcopy(data)))
                
                # Update data reference
                data = result
                
            return data
            
        except Exception as e:
            # Rollback attempt - but original_data is already corrupted
            # because transforms mutated it in-place before we copied it
            print(f"Error during pipeline processing: {e}")
            # This rollback doesn't work because the damage is already done
            return original_data


def create_default_pipeline() -> Pipeline:
    """Create the default processing pipeline."""
    pipeline = Pipeline()
    pipeline.add_transform(sanitize_input)
    pipeline.add_transform(normalize_names)
    pipeline.add_transform(apply_discounts)
    pipeline.add_transform(enrich_timestamps)
    return pipeline
