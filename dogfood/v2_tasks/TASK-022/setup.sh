#!/bin/bash
# TASK-022: Broken tree serialization - loses node order on deserialization
mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-022

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-022/serializer.py << 'EOF'
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
                # Still advance index even for null nodes - this is the bug!
                if i < len(values):
                    i += 1  # BUG: Should not advance if current node is None
                if i < len(values):
                    i += 1  # BUG: Same here
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
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-022/test_tree.py << 'EOF'
"""Tests for tree serialization."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-022')

from serializer import TreeNode, TreeSerializer


def build_tree(values):
    """Build tree from list (level order). None values are skipped."""
    if not values:
        return None
    root = TreeNode(values[0])
    queue = [root]
    i = 1
    while queue and i < len(values):
        node = queue.pop(0)
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def test_simple_tree():
    """Test serialization of a simple tree."""
    #     1
    #    / \
    #   2   3
    root = build_tree([1, 2, 3])
    
    serialized = TreeSerializer.serialize(root)
    print(f"Serialized: {serialized}")
    
    deserialized = TreeSerializer.deserialize(serialized)
    inorder = TreeSerializer.traverse_inorder(deserialized)
    
    assert inorder == [2, 1, 3], f"Expected [2, 1, 3] but got {inorder}"
    print("test_simple_tree PASSED")


def test_unbalanced_left():
    """Test serialization of left-heavy tree."""
    #     1
    #    /
    #   2
    #  /
    # 3
    root = build_tree([1, 2, None, 3, None])
    
    serialized = TreeSerializer.serialize(root)
    print(f"Serialized: {serialized}")
    
    deserialized = TreeSerializer.deserialize(serialized)
    inorder = TreeSerializer.traverse_inorder(deserialized)
    preorder = TreeSerializer.traverse_preorder(deserialized)
    
    assert inorder == [3, 2, 1], f"Expected inorder [3, 2, 1] but got {inorder}"
    assert preorder == [1, 2, 3], f"Expected preorder [1, 2, 3] but got {preorder}"
    print("test_unbalanced_left PASSED")


def test_unbalanced_right():
    """Test serialization of right-heavy tree."""
    #   1
    #    \
    #     2
    #      \
    #       3
    root = build_tree([1, None, 2, None, 3])
    
    serialized = TreeSerializer.serialize(root)
    print(f"Serialized: {serialized}")
    
    deserialized = TreeSerializer.deserialize(serialized)
    inorder = TreeSerializer.traverse_inorder(deserialized)
    
    assert inorder == [1, 2, 3], f"Expected inorder [1, 2, 3] but got {inorder}"
    print("test_unbalanced_right PASSED")


def test_tree_with_gaps():
    """Test serialization of tree with gaps (None nodes in between)."""
    #     1
    #    / \
    #   2   3
    #  /
    # 4
    root = build_tree([1, 2, 3, 4, None, None, None])
    
    serialized = TreeSerializer.serialize(root)
    print(f"Serialized: {serialized}")
    
    deserialized = TreeSerializer.deserialize(serialized)
    inorder = TreeSerializer.traverse_inorder(deserialized)
    preorder = TreeSerializer.traverse_preorder(deserialized)
    
    assert inorder == [4, 2, 1, 3], f"Expected inorder [4, 2, 1, 3] but got {inorder}"
    assert preorder == [1, 2, 4, 3], f"Expected preorder [1, 2, 4, 3] but got {preorder}"
    print("test_tree_with_gaps PASSED")


if __name__ == "__main__":
    test_simple_tree()
    test_unbalanced_left()
    test_unbalanced_right()
    test_tree_with_gaps()
    print("\nAll tests passed!")
EOF