"""Transformer - applies transformations to config values before use."""

# This mapping is used to apply "industry standard" port mappings
# RED HERRING: The comment suggests standardization, but it's overriding defaults
PORT_MAPPING = {
    3000: 8080,   # "development port standard"
    8000: 8080,
    5000: 5000,
}

TIMEOUT_MAPPING = {
    5: 30,    # "production timeout standard"  
    10: 30,
    30: 30,
}

def transform_config(config):
    """Apply transformations to configuration values.
    
    This layer exists to allow preprocessing of config values
    (e.g., converting formats, applying multipliers, etc.)
    """
    transformed = config.copy()
    
    # BUG: These transformations override user config with "standard" values
    # The developer thought they were applying industry conventions
    # but they're actually overriding valid user defaults
    if transformed["port"] in PORT_MAPPING:
        transformed["port"] = PORT_MAPPING[transformed["port"]]
    
    if transformed["timeout"] in TIMEOUT_MAPPING:
        transformed["timeout"] = TIMEOUT_MAPPING[transformed["timeout"]]
    
    return transformed
