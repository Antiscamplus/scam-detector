import os, tempfile, hashlib, time, hmac, base64, json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from detector import transcribe, analyze_text
from line_service import send_scam_alert, reply, THRESHOLD

LOG_FILE = "data/logs.csv"
app = FastAPI(title="Scam Detector API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_last_alert = {}

class TextRequest(BaseModel):
    text: str

def save_log(result, speaker="ไม่ระบุ"):
    os.makedirs("data", exist_ok=True)
    row = {"timestamp":datetime.now().isoformat(),"transcript":result["transcript"],"is_scam":result["is_scam"],
           "risk_score":result["risk_score"],"scam_type":result["scam_type"],
           "red_flags":",".join(result["red_flags"]),"speaker":speaker}
    pd.DataFrame([row]).to_csv(LOG_FILE, mode="a", header=not os.path.exists(LOG_FILE), index=False, encoding="utf-8-sig")

def maybe_alert(result):
    if result["risk_score"] >= THRESHOLD and result["is_scam"]:
        key = hashlib.md5(result["transcript"].encode()).hexdigest()
        if time.time() - _last_alert.get(key,0) > 300:
            _last_alert[key]=time.time(); send_scam_alert(result)

@app.get("/health")
def health(): return {"status":"ok","alert_threshold":THRESHOLD}

@app.post("/analyze-text")
def analyze_text_api(req: TextRequest, bg: BackgroundTasks):
    result = analyze_text(req.text); save_log(result); bg.add_task(maybe_alert, result); return result

@app.post("/analyze-audio")
async def analyze_audio_api(file: UploadFile = File(...), bg: BackgroundTasks = None):
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read()); path=tmp.name
    try:
        result = analyze_text(transcribe(path)); save_log(result); bg.add_task(maybe_alert, result); return result
    finally: os.unlink(path)

@app.post("/test-alert")
def test_alert(bg: BackgroundTasks):
    result = analyze_text("ผมเป็นตำรวจ คุณเกี่ยวข้องกับคดีฟอกเงิน ต้องโอนเงินมาตรวจสอบภายใน 1 ชั่วโมง ห้ามบอกใคร")
    bg.add_task(send_scam_alert, result); return {"sent_to_line":True,"result":result}

@app.get("/logs")
def get_logs(limit:int=500):
    if not os.path.exists(LOG_FILE): return {"logs":[],"total":0}
    df = pd.read_csv(LOG_FILE).fillna("").sort_values("timestamp",ascending=False).head(limit)
    return {"logs":df.to_dict("records"),"total":len(df)}

@app.get("/dataset")
def get_dataset():
    df = pd.read_csv("data/scam_dataset.csv").fillna(""); return {"data":df.to_dict("records")}

@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.body(); secret = os.getenv("LINE_CHANNEL_SECRET","")
    sig = request.headers.get("x-line-signature","")
    expected = base64.b64encode(hmac.new(secret.encode(), body, "sha256").digest()).decode()
    if secret and not hmac.compare_digest(expected, sig): raise HTTPException(400,"Invalid signature")
    for event in json.loads(body).get("events",[]):
        uid = event.get("source",{}).get("userId"); token = event.get("replyToken")
        if event["type"]=="follow":
            reply(f"สวัสดีครับ 🛡️\nUser ID ของคุณคือ:\n{uid}\nนำไปใส่ใน .env ได้เลย", token)
        elif event["type"]=="message" and event["message"]["type"]=="text":
            text = event["message"]["text"]
            if text.lower()=="myid": reply(f"User ID: {uid}", token)
            else:
                r = analyze_text(text); reply(f"ผลวิเคราะห์: เสี่ยง {r['risk_score']}%\nประเภท: {r['scam_type']}\n{r['explanation']}", token)
    return {"ok":True}
