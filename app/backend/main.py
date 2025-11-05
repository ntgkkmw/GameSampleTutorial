"""FastAPI application configuration and router wiring."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/api/save")
def save_game():
    """Placeholder endpoint for future server-side saving."""

    return {"status": "not_implemented"}


@app.get("/api/load")
def load_game():
    """Placeholder endpoint for future server-side loading."""

    return {"status": "not_implemented"}

*** End of File
