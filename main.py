from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="Trello Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TRELLO_KEY = os.environ.get("TRELLO_KEY", "")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN", "")
BASE = "https://api.trello.com/1"

class CardCreate(BaseModel):
    list_id: str
    name: str
    desc: str = ""
    pos: str = "bottom"

class AttachImage(BaseModel):
    card_id: str
    url: str
    name: str = "visual.png"

class CardFull(BaseModel):
    list_id: str
    name: str
    desc: str = ""
    image_url: str = ""
    image_name: str = "visual.png"
    pos: str = "bottom"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/card/create")
async def create_card(data: CardCreate):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE}/cards",
            params={"key": TRELLO_KEY, "token": TRELLO_TOKEN},
            json={"name": data.name, "desc": data.desc, "idList": data.list_id, "pos": data.pos}
        )
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    card = res.json()
    return {"id": card["id"], "name": card["name"], "url": card["url"]}


@app.post("/card/attach")
async def attach_image(data: AttachImage):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE}/cards/{data.card_id}/attachments",
            params={"key": TRELLO_KEY, "token": TRELLO_TOKEN},
            json={"url": data.url, "name": data.name}
        )
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    attach = res.json()
    return {"id": attach["id"], "url": attach.get("url", ""), "name": attach.get("name", "")}


@app.post("/card/create-with-image")
async def create_card_with_image(data: CardFull):
    """Tạo card + attach ảnh trong 1 request"""
    async with httpx.AsyncClient() as client:
        # Tạo card
        res = await client.post(
            f"{BASE}/cards",
            params={"key": TRELLO_KEY, "token": TRELLO_TOKEN},
            json={"name": data.name, "desc": data.desc, "idList": data.list_id, "pos": data.pos}
        )
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        card = res.json()

        # Attach ảnh nếu có
        attach_result = None
        if data.image_url:
            attach_res = await client.post(
                f"{BASE}/cards/{card['id']}/attachments",
                params={"key": TRELLO_KEY, "token": TRELLO_TOKEN},
                json={"url": data.image_url, "name": data.image_name}
            )
            if attach_res.status_code == 200:
                attach_result = attach_res.json().get("url", "")

    return {
        "id": card["id"],
        "name": card["name"],
        "url": card["url"],
        "image_attached": attach_result is not None,
        "image_url": attach_result
    }


@app.get("/boards")
async def get_boards():
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE}/members/me/boards",
            params={"key": TRELLO_KEY, "token": TRELLO_TOKEN, "fields": "id,name"}
        )
    return res.json()


@app.get("/boards/{board_id}/lists")
async def get_lists(board_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE}/boards/{board_id}/lists",
            params={"key": TRELLO_KEY, "token": TRELLO_TOKEN, "fields": "id,name"}
        )
    return res.json()
