from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Any, Dict, List, Optional
from PIL import Image
import uvicorn
import shutil
import os
import datetime
import database
import asyncio
import logging
from config import config
from mahjong_state_tracker import MahjongStateTracker
from mahjong.tile import TilesConverter
from efficiency_engine import EfficiencyEngine, format_suggestions
from stt_service import STTService
from llm_service import LLMService
from vision_service import VisionService, draw_bounding_boxes
from schemas import (
    StartSessionRequest, 
    AnalyzeResponse, 
    EndSessionRequest, 
    ProcessAudioResponse
)

# Configure Logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global Session Trackers
SESSION_TRACKERS: Dict[str, MahjongStateTracker] = {}
EFFICIENCY_ENGINE = EfficiencyEngine()

# Initialize Services
STT_SERVICE = STTService()
LLM_SERVICE = LLMService(
    base_url=config.LLM_BASE_URL,
    api_key=config.LLM_API_KEY,
    model=config.LLM_MODEL
)
VISION_SERVICE = VisionService(
    model_path=config.YOLO_MODEL_PATH,
    class_names_path=config.YOLO_CLASS_NAMES_PATH,
    confidence_threshold=config.YOLO_CONF_THRESHOLD,
    iou_threshold=config.YOLO_IOU_THRESHOLD
)

# Initialize Database
database.init_db()

# YOLO Class to MPSZ Notation Mapping
YOLO_TO_MPSZ_MAPPING = {
    '1B': '1s', '2B': '2s', '3B': '3s', '4B': '4s', '5B': '5s', '6B': '6s', '7B': '7s', '8B': '8s', '9B': '9s',
    '1C': '1m', '2C': '2m', '3C': '3m', '4C': '4m', '5C': '5m', '6C': '6m', '7C': '7m', '8C': '8m', '9C': '9m',
    '1D': '1p', '2D': '2p', '3D': '3p', '4D': '4p', '5D': '5p', '6D': '6p', '7D': '7p', '8D': '8p', '9D': '9p',
    'EW': '1z', 'SW': '2z', 'WW': '3z', 'NW': '4z',
    'WD': '5z', 'GD': '6z', 'RD': '7z',
    '1F': 'f1', '2F': 'f2', '3F': 'f3', '4F': 'f4',
    '1S': 's1', '2S': 's2', '3S': 's3', '4S': 's4',
}

def convert_to_mpsz(yolo_classes: List[str]):
    hand_tiles = []
    bonus_tiles = []
    for cls in yolo_classes:
        mpsz = YOLO_TO_MPSZ_MAPPING.get(cls)
        if mpsz:
            if mpsz.startswith('f') or mpsz.startswith('s'):
                bonus_tiles.append(mpsz)
            else:
                hand_tiles.append(mpsz)
        else:
            hand_tiles.append(cls)
    # 四川麻将仅万/筒/条；识别结果中的字牌不进入手牌列表
    hand_tiles = [
        t for t in hand_tiles
        if isinstance(t, str) and len(t) >= 2 and t[-1] in "mps"
    ]
    return hand_tiles, bonus_tiles

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.post("/api/start-session")
async def start_session(request: StartSessionRequest):
    logger.info(f"Received Start Session request: session_id={request.session_id}")
    database.create_or_update_session(request.session_id)
    SESSION_TRACKERS[request.session_id] = MahjongStateTracker()
    return {"status": "success", "session_id": request.session_id}

@app.post("/api/analyze-hand", response_model=AnalyzeResponse)
async def analyze_hand(
    image: UploadFile = File(...),
    session_id: str = Form(...),
    incoming_tile: Optional[str] = Form(None)
):
    start_time = datetime.datetime.now()
    steps_log = []
    database.create_or_update_session(session_id)

    timestamp = int(start_time.timestamp() * 1000)
    file_extension = os.path.splitext(image.filename)[1] or ".jpg"
    safe_filename = f"{session_id}_{timestamp}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # State Tracking
    tracker = SESSION_TRACKERS.get(session_id)
    if not tracker:
        tracker = MahjongStateTracker()
        SESSION_TRACKERS[session_id] = tracker

    user_hand: List[str] = []
    melded_tiles: List[str] = []
    annotated_path = None
    tracker.photo_count += 1

    try:
        predictions = VISION_SERVICE.detect_objects(file_path)
        if predictions:
            yolo_classes = [p.get("class", "") for p in predictions]
            user_hand, _bonus = convert_to_mpsz(yolo_classes)
            steps_log.append({"step": "yolo", "count": len(predictions), "hand_len": len(user_hand)})
    except Exception as e:
        logger.exception("Vision inference failed: %s", e)
        steps_log.append({"step": "yolo_error", "error": str(e)})

    # 贪心牌效：需恰好 14 张序数牌（川麻 108 张，已在 convert_to_mpsz 中去掉字牌）
    if len(user_hand) == 14:
        result = EFFICIENCY_ENGINE.calculate_best_discard(user_hand, melds=[])
    else:
        result = {
            "message": (
                f"当前识别到 {len(user_hand)} 张牌，需 14 张才能计算最佳出牌（向听+进张贪心）。"
                "请调整光线或重拍含完整手牌的画面。"
            )
        }
    suggested_play = format_suggestions(result)

    response_data = AnalyzeResponse(
        user_hand=user_hand,
        melded_tiles=melded_tiles,
        suggested_play=suggested_play, 
        annotated_image_path=None,
        action_detected="PHOTO_ANALYSIS",
        warning=None,
        is_stable=True
    )
    
    database.log_interaction(session_id=session_id, image_path=f"/static/uploads/{safe_filename}", steps=steps_log, response=response_data.dict())
    return response_data

@app.post("/api/process-audio", response_model=ProcessAudioResponse)
async def process_audio(audio: UploadFile = File(...), session_id: str = Form(...)):
    database.create_or_update_session(session_id)
    if session_id not in SESSION_TRACKERS:
        SESSION_TRACKERS[session_id] = MahjongStateTracker()

    timestamp = int(datetime.datetime.now().timestamp() * 1000)
    filename = f"{session_id}_{timestamp}{os.path.splitext(audio.filename)[1] or '.wav'}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
        
    transcript = STT_SERVICE.transcribe(file_path)
    events = LLM_SERVICE.analyze_game_events(transcript) if transcript else []
    tracker = SESSION_TRACKERS[session_id]
    update_result = tracker.update_visible_tiles(events)

    response_data = {
        "transcript": transcript,
        "events": events,
        "updated_visible_tiles_count": update_result["updated_count"],
        "details": update_result["details"]
    }
    database.log_interaction(session_id=session_id, image_path=None, steps=[], response=response_data)
    return ProcessAudioResponse(**response_data)

@app.post("/api/end-session")
async def end_session(request: EndSessionRequest):
    database.end_session(request.session_id)
    SESSION_TRACKERS.pop(request.session_id, None)
    return {"status": "success", "message": "Session ended"}

@app.get("/api/history/sessions")
async def get_history_sessions():
    return database.get_all_sessions()

@app.get("/api/history/details/{session_id}")
async def get_history_details(session_id: str):
    return database.get_session_details(session_id) or {"error": "Session not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
