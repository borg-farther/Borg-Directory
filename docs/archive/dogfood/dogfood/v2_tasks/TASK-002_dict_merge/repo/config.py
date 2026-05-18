class Config:
    """Configuration manager with layered defaults."""
    
    def __init__(self, defaults=None):
        self._data = defaults if defaults is not None else {}
    
    def merge(self, overrides):
        """Merge overrides into config. Should not mutate the overrides dict."""
        for key, value in overrides.items():
            if key in self._data and isinstance(self._data[key], dict) and isinstance(value, dict):
                # BUG: shallow reference — mutates the original overrides dict
                self._data[key] = value
                self._data[key].update(self._data.get(key, {}))
            else:
                self._data[key] = value
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def to_dict(self):
        return dict(self._data)
