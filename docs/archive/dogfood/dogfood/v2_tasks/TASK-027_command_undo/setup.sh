#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/editor.py << 'PYEOF'
class TextEditor:
    """Simple text editor with undo support using command pattern."""
    
    def __init__(self):
        self.text = ""
        self.cursor = 0
        self._undo_stack = []
    
    def insert(self, s):
        """Insert string at cursor position."""
        self._undo_stack.append(("delete", self.cursor, len(s)))
        self.text = self.text[:self.cursor] + s + self.text[self.cursor:]
        self.cursor += len(s)
    
    def delete(self, count):
        """Delete count characters before cursor."""
        if count > self.cursor:
            count = self.cursor
        deleted = self.text[self.cursor - count:self.cursor]
        # BUG: undo record saves wrong cursor position
        self._undo_stack.append(("insert", self.cursor, deleted))
        self.text = self.text[:self.cursor - count] + self.text[self.cursor:]
        self.cursor -= count
    
    def undo(self):
        """Undo last operation."""
        if not self._undo_stack:
            return
        
        op, pos, data = self._undo_stack.pop()
        if op == "insert":
            # Undo a delete: re-insert the deleted text
            # BUG: uses current cursor, should use saved position
            self.text = self.text[:pos] + data + self.text[pos:]
            self.cursor = pos + len(data)
        elif op == "delete":
            # Undo an insert: delete the inserted text
            self.text = self.text[:pos] + self.text[pos + data:]
            self.cursor = pos
PYEOF

cat > repo/test_editor.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from editor import TextEditor

def test_insert_undo():
    e = TextEditor()
    e.insert("hello")
    e.insert(" world")
    assert e.text == "hello world"
    e.undo()
    assert e.text == "hello", f"After undo: '{e.text}'"
    assert e.cursor == 5, f"Cursor should be 5, got {e.cursor}"

def test_delete_undo():
    e = TextEditor()
    e.insert("hello world")
    e.cursor = 5  # Position after "hello"
    e.delete(5)  # Delete "hello"
    assert e.text == " world", f"After delete: '{e.text}'"
    e.undo()
    assert e.text == "hello world", f"After undo: '{e.text}'"
    assert e.cursor == 5, f"Cursor should be 5, got {e.cursor}"

def test_insert_delete_undo_sequence():
    e = TextEditor()
    e.insert("abc")
    e.insert("def")
    e.delete(3)  # Delete "def"
    assert e.text == "abc", f"After delete: '{e.text}'"
    e.undo()  # Undo delete -> restore "def"
    assert e.text == "abcdef", f"After undo delete: '{e.text}'"
    e.undo()  # Undo second insert
    assert e.text == "abc", f"After undo insert: '{e.text}'"

if __name__ == "__main__":
    tests = [test_insert_undo, test_delete_undo, test_insert_delete_undo_sequence]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
