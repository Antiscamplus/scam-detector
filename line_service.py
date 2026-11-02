import os, requests
from datetime import datetime

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
ALERT_TO = os.getenv("LINE_ALERT_USER_ID")
THRESHOLD = int(os.getenv("ALERT_THRESHOLD","80"))

def build_flex(result):
    flags = "\n".join([f"• {f}" for f in result["red_flags"]]) or "• ไม่พบ"
    return {"type":"flex","altText":f"🚨 พบสแกมเสี่ยง {result['risk_score']}%",
        "contents":{"type":"bubble",
            "header":{"type":"box","layout":"vertical","backgroundColor":"#dc2626","contents":[{"type":"text","text":"🚨 แจ้งเตือนสแกมเมอร์!","color":"#ffffff","weight":"bold","size":"lg"}]},
            "body":{"type":"box","layout":"vertical","spacing":"md","contents":[
                {"type":"text","text":f"ความเสี่ยง: {result['risk_score']}%","weight":"bold","size":"xl","color":"#dc2626"},
                {"type":"text","text":f"ประเภท: {result['scam_type']}"},
                {"type":"separator"},
                {"type":"text","text":"พฤติกรรมที่พบ:","weight":"bold"},
                {"type":"text","text":flags,"wrap":True,"size":"sm"},
                {"type":"text","text":f"\"{result['transcript'][:150]}...\"","wrap":True,"size":"sm","color":"#666666"},
                {"type":"text","text":datetime.now().strftime("%d/%m/%Y %H:%M"),"size":"xs","color":"#aaaaaa"}]}}}

def send_scam_alert(result):
    if not TOKEN or not ALERT_TO: return False
    r = requests.post("https://api.line.me/v2/bot/message/push",
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},
        json={"to":ALERT_TO,"messages":[build_flex(result)]}, timeout=10)
    return r.status_code==200

def reply(text, reply_token):
    requests.post("https://api.line.me/v2/bot/message/reply",
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},
        json={"replyToken":reply_token,"messages":[{"type":"text","text":text}]}, timeout=10)
