import os
from app.main import app

routes = []
for route in app.routes:
    methods = getattr(route, "methods", None)
    path = getattr(route, "path", None)
    name = getattr(route, "name", None)
    if path:
        routes.append((path, sorted(list(methods)) if methods else [], name))

routes.sort(key=lambda x: x[0])
print(f"Total mounted routes: {len(routes)}")
for path, methods, name in routes:
    if path.startswith("/api"):
        print(f"{', '.join(methods):<15} {path}  ({name})")
