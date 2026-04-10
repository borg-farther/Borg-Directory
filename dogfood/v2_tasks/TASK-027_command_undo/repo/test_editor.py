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
