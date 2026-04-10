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
