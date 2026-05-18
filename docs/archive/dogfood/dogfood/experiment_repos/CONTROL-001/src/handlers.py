"""Request handlers."""
# TODO: Add rate limiting


def handle_get(request):
    """Handle GET request."""
    return {"status": "ok"}


def handle_post(request):
    """Handle POST request."""
    return {"status": "created"}
