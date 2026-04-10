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
