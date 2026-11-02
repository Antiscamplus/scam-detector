import streamlit as st, requests, pandas as pd, json, os
import plotly.graph_objects as go, plotly.express as px

st.set_page_config(page_title="AI Scam Detector", page_icon="🛡️", layout="wide")
DEFAULT_API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def api_get(path, url):
    r=requests.get(f"{url}{path}",timeout=30); r.raise_for_status(); return r.json()

def gauge(score):
    c="#ef4444" if score>=70 else "#f59e0b" if score>=40 else "#22c55e"
    f=go.Figure(go.Indicator(mode="gauge+number",value=score,title={"text":"Risk Score"},gauge={"axis":{"range":[0,100]},"bar":{"color":c}}))
    f.update_layout(height=280,paper_bgcolor="rgba(0,0,0,0)"); return f

with st.sidebar:
    st.title("⚙️ การเชื่อมต่อ Server")
    api_url = st.text_input("FastAPI Server URL", value=st.secrets.get("API_BASE_URL", DEFAULT_API) if hasattr(st,"secrets") else DEFAULT_API).rstrip("/")
    try:
        h=api_get("/health",api_url); st.success(f"✅ เชื่อมต่อสำเร็จ | แจ้งเตือน LINE >= {h['alert_threshold']}%")
    except: st.error("❌ เชื่อมต่อ Server ไม่ได้ - รัน: uvicorn main_api:app --host 0.0.0.0 --port 8000")
    if st.button("🔔 ทดสอบ LINE Alert",use_container_width=True):
        try: requests.post(f"{api_url}/test-alert",timeout=60); st.success("ส่งแล้ว เช็ค LINE เลย")
        except Exception as e: st.error(str(e))

st.title("🛡️ AI Scam Call Detector")
tab1,tab2,tab3,tab4 = st.tabs(["🎙️ วิเคราะห์","📊 ฐานข้อมูล RAG","📜 ประวัติ","📈 Dashboard"])

with tab1:
    mode=st.radio("วิธีนำเข้า",["อัปโหลดไฟล์เสียง","พิมพ์ข้อความทดสอบ"],horizontal=True)
    if mode=="พิมพ์ข้อความทดสอบ":
        text=st.text_area("ข้อความ",value="ผมเป็นตำรวจ คุณเกี่ยวข้องกับคดีฟอกเงิน ต้องโอนเงินมาตรวจสอบภายใน 1 ชั่วโมง ห้ามบอกใคร",height=120)
        if st.button("🔍 วิเคราะห์",type="primary",use_container_width=True):
            with st.spinner("กำลังวิเคราะห์..."):
                r=requests.post(f"{api_url}/analyze-text",json={"text":text},timeout=60); st.session_state["result"]=r.json()
    else:
        up=st.file_uploader("อัปโหลดไฟล์เสียง",type=["mp3","wav","m4a","ogg"])
        try: rec=st.audio_input("หรืออัดเสียงสด")
        except: rec=None
        f=up if up else rec
        if f:
            st.audio(f)
            if st.button("🎧 ถอดเสียง + วิเคราะห์",type="primary",use_container_width=True):
                with st.spinner("Server กำลังถอดเสียง..."):
                    files={"file":(getattr(f,"name","audio.wav"),f.getvalue(),getattr(f,"type","audio/wav"))}
                    r=requests.post(f"{api_url}/analyze-audio",files=files,timeout=300); st.session_state["result"]=r.json()
    if "result" in st.session_state:
        r=st.session_state["result"]; st.divider()
        if r.get("transcript"): st.text_area("📝 ข้อความที่ถอดได้",value=r["transcript"],height=120)
        c1,c2=st.columns([1,2])
        with c1: st.plotly_chart(gauge(r["risk_score"]),use_container_width=True)
        with c2:
            if r["risk_score"]>=80: st.error(f"### 🚨 เสี่ยงสูงมาก! ({r['scam_type']}) แจ้งเตือน LINE แล้ว")
            elif r["risk_score"]>=40: st.warning(f"### ⚠️ เสี่ยงปานกลาง ({r['scam_type']})")
            else: st.success("### ✅ เสี่ยงต่ำ - ดูปกติ")
            st.write(r["explanation"]); st.write("**🚩 Red Flags:**")
            for x in r.get("red_flags",[]): st.write(f"- {x}")
        for d in r.get("rag_matches",[]):
            with st.expander(f"{'🔴 SCAM' if d['label']==1 else '🟢 NORMAL'} | {d['scam_type']} | คล้าย {d['similarity']}%"): st.write(d["text"])
        st.download_button("⬇️ ดาวน์โหลดรายงาน JSON",json.dumps(r,ensure_ascii=False,indent=2),"scam_report.json")

with tab2:
    if st.button("🔄 โหลดข้อมูล"): st.dataframe(pd.DataFrame(api_get("/dataset",api_url)["data"]),use_container_width=True)
with tab3:
    if st.button("🔄 รีเฟรชประวัติ"): st.dataframe(pd.DataFrame(api_get("/logs?limit=200",api_url)["logs"]),use_container_width=True)
with tab4:
    try:
        df=pd.DataFrame(api_get("/logs?limit=1000",api_url)["logs"])
        if not df.empty:
            df["is_scam"]=df["is_scam"].astype(str).str.lower().isin(["true","1"])
            k1,k2,k3=st.columns(3); k1.metric("ตรวจทั้งหมด",len(df)); k2.metric("พบสแกม",int(df["is_scam"].sum())); k3.metric("Risk เฉลี่ย",f"{df['risk_score'].mean():.1f}%")
            c1,c2=st.columns(2)
            with c1: st.plotly_chart(px.pie(df["is_scam"].value_counts().rename(index={True:"สแกม",False:"ปกติ"}).reset_index(),values="count",names="is_scam",hole=0.5,title="สแกม vs ปกติ"),use_container_width=True)
            with c2: st.plotly_chart(px.bar(df[df["is_scam"]].groupby("scam_type").size().reset_index(name="count"),x="scam_type",y="count",title="แยกตามประเภท"),use_container_width=True)
            st.dataframe(df.nlargest(10,"risk_score")[["timestamp","scam_type","risk_score","transcript"]],use_container_width=True)
        else: st.info("ยังไม่มีข้อมูล")
    except Exception as e: st.warning(str(e))
