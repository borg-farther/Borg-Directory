"""Matrix operations including transpose and multiply."""
from typing import List


def create_matrix(rows: int, cols: int, default: float = 0.0) -> List[List[float]]:
    """Create a matrix with given dimensions."""
    return [[default for _ in range(cols)] for _ in range(rows)]


def transpose(matrix: List[List[float]]) -> List[List[float]]:
    """Transpose a matrix (swap rows and columns)."""
    if not matrix:
        return []
    rows = len(matrix)
    cols = len(matrix[0])
    result = create_matrix(cols, rows)
    for i in range(rows):
        for j in range(cols):
            result[j][i] = matrix[i][j]
    return result


def multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    """Multiply two matrices."""
    if not a or not b:
        return []
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])
    
    if cols_a != rows_b:
        raise ValueError(f"Incompatible dimensions: {cols_a} != {rows_b}")
    
    result = create_matrix(rows_a, cols_b)
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    return result


def matmul_backward(x: List[List[float]], w: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    """Compute backward pass of matmul: dL/dX = dL/dY @ W.T
    But the bug is applying transpose in the wrong order!
    """
    # dL/dY is the upstream gradient (same shape as output)
    # For simplicity, assume upstream gradient is all ones
    upstream = create_matrix(len(x), len(w[0]), 1.0)
    
    # Bug: We should compute dL/dX = upstream @ W.T
    # But we're computing upstream.T @ W instead!
    # This is wrong because dimensions don't even work out correctly
    # for the typical case.
    w_transposed = transpose(w)
    
    # The bug: transpose is applied in wrong order
    # We want (upstream @ W.T) but we do (upstream.T @ W)
    # Actually wait, let me reconsider. For X @ W + b = Y:
    # dL/dX = dL/dY @ W.T  (correct)
    # dL/dW = X.T @ dL/dY   (correct for this part)
    # 
    # But if we're just computing dL/dX given upstream (dL/dY),
    # it should be: upstream @ W.T
    #
    # Bug code does: transpose(upstream) @ w
    # Which is wrong!
    
    return multiply(upstream, w_transposed)


def matmul_backward_correct(x: List[List[float]], w: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    """Correct implementation of backward pass."""
    upstream = create_matrix(len(x), len(w[0]), 1.0)
    w_transposed = transpose(w)
    return multiply(upstream, w_transposed)


def test_matmul_backward():
    """Test that matmul backward gives correct gradient shape."""
    # Input x: 2x3, Weights w: 3x4, Bias b: 1x4
    x = [[1, 0, 2], [0, 1, 0]]  # 2x3
    w = [[1, 2, 3, 4], [5, 6, 7, 8], [1, 1, 1, 1]]  # 3x4
    b = [[0, 0, 0, 0]]  # 1x4
    
    # Forward: X @ W + b = Y
    # Y should be 2x4
    y = multiply(x, w)
    assert len(y) == 2 and len(y[0]) == 4, f"Y shape should be 2x4 but got {len(y)}x{len(y[0]) if y else 0}"
    
    # Backward: dL/dX = dL/dY @ W.T
    # dL/dY is same shape as Y (2x4)
    # W.T is 4x3
    # So dL/dX should be 2x3 (same as X)
    try:
        dX = matmul_backward(x, w, b)
        # This should work if dimensions are correct
        assert len(dX) == 2 and len(dX[0]) == 3, f"dX shape should be 2x3 but got {len(dX)}x{len(dX[0]) if dX else 0}"
    except ValueError as e:
        # Bug causes dimension mismatch
        raise AssertionError(f"matmul_backward failed with dimensions: {e}")
    
    print("test_matmul_backward PASSED")


def test_transpose_preserves_shape_info():
    """Test that transpose correctly handles shape information."""
    m = [[1, 2, 3], [4, 5, 6]]  # 2x3
    t = transpose(m)  # should be 3x2
    
    assert len(t) == 3, f"Transpose should have 3 rows but got {len(t)}"
    assert len(t[0]) == 2, f"Transpose should have 2 cols but got {len(t[0])}"
    
    # Check content
    assert t[0] == [1, 4], f"t[0] should be [1, 4] but got {t[0]}"
    assert t[2] == [3, 6], f"t[2] should be [3, 6] but got {t[2]}"
    
    print("test_transpose_preserves_shape_info PASSED")


def test_matrix_multiply_dimensions():
    """Test matrix multiply gives correct dimensions."""
    a = [[1, 2], [3, 4], [5, 6]]  # 3x2
    b = [[1, 2, 3], [4, 5, 6]]  # 2x3
    
    result = multiply(a, b)
    
    assert len(result) == 3, f"Result should have 3 rows"
    assert len(result[0]) == 3, f"Result should have 3 cols"
    
    # Check some values
    assert result[0][0] == 1*1 + 2*4 == 9
    assert result[1][1] == 3*2 + 4*5 == 26
    
    print("test_matrix_multiply_dimensions PASSED")


if __name__ == "__main__":
    test_transpose_preserves_shape_info()
    test_matrix_multiply_dimensions()
    test_matmul_backward()
    print("\nAll tests passed!")
