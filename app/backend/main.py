"""FastAPI application configuration and router wiring."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from models.game import APP_VERSION, GameData
from routes import battles, players, shops, world

app = FastAPI(title="Retro RPG API", version=APP_VERSION)

game_data = GameData()
app.add_middleware(
    CORSMiddleware,
    allow_origins=game_data.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.data = game_data
app.state.battles = {}

app.include_router(players.router)
app.include_router(world.router)
app.include_router(battles.router)
app.include_router(shops.router)


def _frontend_dir() -> Path | None:
    """Return the path to the bundled frontend directory if it exists."""

    candidate = Path(__file__).resolve().parent.parent / "frontend"
    return candidate if candidate.exists() else None


if (frontend_dir := _frontend_dir()) is not None:
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend_static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def frontend_index() -> HTMLResponse:
        """Serve the single page app entrypoint."""

        index_path = frontend_dir / "index.html"
        try:
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:  # pragma: no cover - development safeguard
            raise HTTPException(status_code=404, detail="index.html not found") from exc


@app.post("/api/save")
def save_game():
    """Placeholder endpoint for future server-side saving."""

    return {"status": "not_implemented"}


@app.get("/api/load")
def load_game():
    """Placeholder endpoint for future server-side loading."""

    return {"status": "not_implemented"}
