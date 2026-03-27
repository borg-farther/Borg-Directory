"""Check agent stats after update_agent_stats."""
import tempfile
from pathlib import Path
from guild.db.store import GuildStore

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "test.db"
    store = GuildStore(str(db_path))
    store.register_agent("test-agent", operator="test-op")
    
    # Check initial state
    agent = store.get_agent("test-agent")
    print("Initial:", {k: agent[k] for k in ['contribution_score', 'packs_published', 'packs_consumed', 'feedback_given']})
    
    # Update stats
    store.update_agent_stats(
        "test-agent",
        packs_consumed=50,
        packs_published=1,
        feedback_given=0,
    )
    
    # Check after update
    agent = store.get_agent("test-agent")
    print("After update:", {k: agent[k] for k in ['contribution_score', 'packs_published', 'packs_consumed', 'feedback_given']})
    
    store.close()
