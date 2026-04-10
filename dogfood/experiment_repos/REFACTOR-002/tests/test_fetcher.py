"""Tests for URL fetcher - verifies correctness."""
import pytest
from src.fetcher import fetch_url_callback, fetch_multiple_urls_callbacks


def test_fetch_single_url_success():
    """Test fetching a single URL successfully."""
    result = []

    def on_complete(err, data):
        result.append((err, data))

    fetch_url_callback('https://example.com', on_complete)

    assert len(result) == 1
    err, data = result[0]
    assert err is None
    assert 'example.com' in data


def test_fetch_single_url_error():
    """Test fetching an invalid URL."""
    result = []

    def on_complete(err, data):
        result.append((err, data))

    fetch_url_callback('invalid-url', on_complete)

    assert len(result) == 1
    err, data = result[0]
    assert err is not None
    assert data is None


def test_fetch_multiple_urls():
    """Test fetching multiple URLs."""
    urls = [
        'https://example1.com',
        'https://example2.com',
        'https://example3.com',
    ]
    all_results = []
    all_errors = []

    def on_all_complete(results, errors):
        all_results.extend(results)
        all_errors.extend(errors)

    fetch_multiple_urls_callbacks(urls, on_all_complete)

    # All URLs should be fetched
    assert len(all_results) == 3
    assert len(all_errors) == 0


def test_fetch_multiple_urls_with_invalid():
    """Test fetching multiple URLs with one invalid."""
    urls = [
        'https://example1.com',
        'invalid-url',
        'https://example3.com',
    ]
    all_results = []
    all_errors = []

    def on_all_complete(results, errors):
        all_results.extend(results)
        all_errors.extend(errors)

    fetch_multiple_urls_callbacks(urls, on_all_complete)

    assert len(all_results) == 2
    assert len(all_errors) == 1
