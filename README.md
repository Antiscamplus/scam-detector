# 🛡️ AI Scam Call Detector

ระบบตรวจจับแก๊งคอลเซ็นเตอร์จากเสียงพูดภาษาไทย ด้วย Whisper + RAG + LINE OA Alert

## Features
- แปลงเสียงไทยเป็นข้อความด้วย faster-whisper
- ค้นหาสคริปต์สแกมเมอร์ด้วย RAG (ChromaDB + bge-m3)
- วิเคราะห์ Red Flags และให้คะแนนความเสี่ยง 0-100%
- แยกเสียงผู้พูด 2 คนด้วย pyannote (Optional)
- แจ้งเตือน LINE OA อัตโนมัติเมื่อเสี่ยง >= 80%
- Dashboard สรุปสถิติ

## Quick Start (Docker)
1. Copy `.env.example` เป็น `.env` แล้วใส่ LINE Token
2. รัน `docker compose up -d --build`
3. เปิดเว็บ https://scam.antiscamplus.org

## Run Local (Dev)
Terminal 1: `uvicorn main_api:app --port 8000`
Terminal 2: `streamlit run app.py`

## LINE Webhook
`https://scam.antiscamplus.org/line/webhook`
