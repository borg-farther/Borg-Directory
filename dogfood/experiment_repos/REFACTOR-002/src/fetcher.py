"""URL fetcher with nested callbacks - callback hell."""
import time


def fetch_url_callback(url, callback):
    """
    Simulate fetching a URL with callback.
    This is callback-style code that leads to callback hell.
    """
    def on_success(data):
        callback(None, data)

    def on_error(error):
        callback(error, None)

    # Simulate async fetch
    time.sleep(0.01)
    if url.startswith('http'):
        on_success(f'Data from {url}')
    else:
        on_error(f'Invalid URL: {url}')


def fetch_multiple_urls_callbacks(urls, on_all_complete):
    """
    Fetch multiple URLs sequentially using callbacks.
    THIS IS CALLBACK HELL - deeply nested callbacks.
    """
    results = []
    errors = []

    def handle_result(url, error, data):
        if error:
            errors.append({'url': url, 'error': error})
        else:
            results.append({'url': url, 'data': data})

        # Check if all complete
        if len(results) + len(errors) == len(urls):
            on_all_complete(results, errors)

    # Callback hell: nested callbacks for sequential fetches
    def fetch_next(index):
        if index >= len(urls):
            on_all_complete(results, errors)
            return

        url = urls[index]

        def on_url_fetched(err, data):
            if err:
                errors.append({'url': url, 'error': err})
            else:
                results.append({'url': url, 'data': data})

            # NEXT CALLBACK HELL - fetch next URL
            if index + 1 < len(urls):
                next_url = urls[index + 1]

                def on_next_url_fetched(err2, data2):
                    if err2:
                        errors.append({'url': next_url, 'error': err2})
                    else:
                        results.append({'url': next_url, 'data': data2})

                    # ANOTHER CALLBACK HELL - fetch next
                    if index + 2 < len(urls):
                        next_next_url = urls[index + 2]

                        def on_next_next_url_fetched(err3, data3):
                            if err3:
                                errors.append({'url': next_next_url, 'error': err3})
                            else:
                                results.append({'url': next_next_url, 'data': data3})

                            if index + 3 < len(urls):
                                # This pattern continues deeper...
                                fetch_next(index + 3)
                            else:
                                on_all_complete(results, errors)

                        fetch_url_callback(next_next_url, on_next_next_url_fetched)
                    else:
                        on_all_complete(results, errors)

                fetch_url_callback(next_url, on_next_url_fetched)
            else:
                on_all_complete(results, errors)

        fetch_url_callback(url, on_url_fetched)

    fetch_next(0)


def fetch_urls_simple(urls):
    """
    Simple synchronous fetch - works but not async.
    """
    results = []
    for url in urls:
        fetch_url_callback(url, lambda err, data: results.append(
            {'url': url, 'data': data} if not err else {'url': url, 'error': err}
        ))
    return results
