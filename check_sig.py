from guild.db.store import GuildStore
import inspect
print("register_agent:", inspect.signature(GuildStore.register_agent))
print("add_pack:", inspect.signature(GuildStore.add_pack))
