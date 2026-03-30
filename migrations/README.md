Alembic migrations live here. Apply with:

```bash
alembic upgrade head
```

Set `DATABASE_URL` to a sync URL for offline tooling (e.g. `sqlite:///./app.db`). The app runtime uses async SQLAlchemy URLs such as `sqlite+aiosqlite:///./app.db`.
