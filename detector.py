import os, pandas as pd

DATASET_FILE = "data/scam_dataset.csv"

RED_FLAG_KEYWORDS = {
    "อ้างเป็นหน่วยงาน/ตำรวจ/ธนาคาร": ["ตำรวจ","ธนาคาร","dhl","สรรพากร","ศาล","เจ้าหน้าที่"],
    "สร้างความเร่งด่วน": ["ภายใน 1 ชั่วโมง","ภายในวันนี้","ด่วน","ทันที","จะถูกอายัด","ออกหมายจับ"],
    "ขอให้โอนเงิน": ["โอนเงิน","โอนมา","ค่าดำเนินการ","ค่าธรรมเนียมก่อน"],
    "ขอข้อมูลลับ": ["otp","เลขบัตร","รหัสผ่าน","เลขหลังบัตร"],
    "ห้ามบอกใคร/ห้ามวางสาย": ["ห้ามบอกใคร","อย่าบอกใคร","ห้ามวางสาย","ความลับ"],
    "ผลตอบแทนสูงเกินจริง": ["การันตี","ไม่มีขาดทุน","ผลตอบแทน 30","รวยเร็ว","ฝาก 1000 ได้"],
}

_models = {}

def load_models():
    if "whisper" in _models:
        return _models
    from faster_whisper import WhisperModel
    from sentence_transformers import SentenceTransformer
    import chromadb, torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _models["whisper"] = WhisperModel("small", device=device, compute_type="float16" if device=="cuda" else "int8")
    _models["embed"] = SentenceTransformer("BAAI/bge-m3")

    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("scam_patterns")
        if collection.count() == 0: raise Exception("empty")
    except:
        try: client.delete_collection("scam_patterns")
        except: pass
        collection = client.create_collection("scam_patterns", metadata={"hnsw:space":"cosine"})
        df = pd.read_csv(DATASET_FILE)
        embs = _models["embed"].encode(df["text"].tolist()).tolist()
        collection.add(documents=df["text"].tolist(), embeddings=embs,
            metadatas=df[["label","scam_type","red_flags"]].to_dict("records"),
            ids=[str(i) for i in range(len(df))])
    _models["collection"] = collection
    return _models

def transcribe(audio_path):
    segments, _ = load_models()["whisper"].transcribe(audio_path, language="th", beam_size=5)
    return "".join(s.text for s in segments).strip()

def transcribe_with_timestamps(audio_path):
    segments, _ = load_models()["whisper"].transcribe(audio_path, language="th", beam_size=5)
    segs = [{"start":s.start,"end":s.end,"text":s.text} for s in segments]
    return "".join(s["text"] for s in segs).strip(), segs

def detect_red_flags(text):
    low = text.lower()
    return [f for f,kws in RED_FLAG_KEYWORDS.items() if any(k.lower() in low for k in kws)]

def analyze_text(transcript):
    m = load_models()
    emb = m["embed"].encode([transcript]).tolist()
    res = m["collection"].query(query_embeddings=emb, n_results=5)
    rag = [{"text":d,"label":int(meta["label"]),"scam_type":meta["scam_type"],"red_flags":meta["red_flags"],"similarity":round((1-dist)*100,2)}
           for d,meta,dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
    flags = detect_red_flags(transcript)
    scam_sims = [r["similarity"] for r in rag if r["label"]==1]
    max_sim = max(scam_sims) if scam_sims else 0
    risk = int(min(100, (max_sim*0.7)+(len(flags)*12)))
    is_scam = risk >= 50
    return {"transcript":transcript,"is_scam":is_scam,"risk_score":risk,
            "scam_type": rag[0]["scam_type"] if is_scam and rag else "normal",
            "red_flags":flags,"evidence":[r["text"] for r in rag[:2]] if is_scam else [],
            "explanation":f"พบความคล้ายกับสคริปต์สแกม {max_sim:.1f}% และพบพฤติกรรมเสี่ยง {len(flags)} ข้อ",
            "rag_matches":rag}
