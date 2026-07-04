"""
HTTP middleware package for AFianco backend.

Each middleware is a separate file with a clear single responsibility:
    - request_context_middleware: Per-request correlation/request ID propagation

Middleware are wired in server.py via app.add_middleware(...).
"""
