import guild
print(f"guild v{guild.__version__} loaded OK")
print(f"Exports: {[x for x in dir(guild) if not x.startswith('_')]}")
