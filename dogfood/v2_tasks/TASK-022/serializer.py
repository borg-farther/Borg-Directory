"""Tree serialization and deserialization."""
from typing import Optional, List, Any


class TreeNode:
    """A node in a binary tree."""
    def __init__(self, value: int, left: Optional['TreeNode'] = None, right: Optional['TreeNode'] = None):
        self.value = value
        self.left = left
        self.right = right
    
    def __repr__(self):
        return f"TreeNode({self.value})"


class TreeSerializer:
    """Serializer for binary trees."""
    
    @staticmethod
    def serialize(root: Optional[TreeNode]) -> str:
        """Serialize tree to string using level-order (BFS) traversal."""
        if not root:
            return ""
        
        result = []
        queue = [root]
        
        while queue:
            node = queue.pop(0)
            if node is None:
                result.append("#")
            else:
                result.append(str(node.value))
                queue.append(node.left)
                queue.append(node.right)
        
        # Remove trailing None/# markers to save space
        while result and result[-1] == "#":
            result.pop()
        
        return ",".join(result)
    
    @staticmethod
    def deserialize(data: str) -> Optional[TreeNode]:
        """Deserialize string to tree using level-order (BFS) traversal."""
        if not data:
            return None
        
        values = data.split(",")
        
        if not values or values[0] == "#":
            return None
        
        root = TreeNode(int(values[0]))
        queue = [root]
        i = 1
        
        # BUG: The deserialization uses a simple left-right pattern
        # but doesn't correctly handle the queue index advancement.
        # When we skip a None node, we still advance i for its children,
        # causing misalignment.
        while queue and i < len(values):
            node = queue.pop(0)
            
            if node is None:
                continue
            
            # Left child
            if i < len(values) and values[i] != "#":
                node.left = TreeNode(int(values[i]))
                queue.append(node.left)
            else:
                queue.append(None)
            i += 1
            
            # Right child
            if i < len(values) and values[i] != "#":
                node.right = TreeNode(int(values[i]))
                queue.append(node.right)
            else:
                queue.append(None)
            i += 1
        
        return root
    
    @staticmethod
    def traverse_inorder(root: Optional[TreeNode]) -> List[int]:
        """Get inorder traversal of tree."""
        result = []
        def _traverse(node):
            if node:
                _traverse(node.left)
                result.append(node.value)
                _traverse(node.right)
        _traverse(root)
        return result
    
    @staticmethod
    def traverse_preorder(root: Optional[TreeNode]) -> List[int]:
        """Get preorder traversal of tree."""
        result = []
        def _traverse(node):
            if node:
                result.append(node.value)
                _traverse(node.left)
                _traverse(node.right)
        _traverse(root)
        return result
