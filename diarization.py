import subprocess

def convert_to_wav_16k(input_path):
    out = input_path + "_16k.wav"
    subprocess.run(["ffmpeg","-y","-i",input_path,"-ar","16000","-ac","1",out],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out

def load_pipeline(hf_token):
    from pyannote.audio import Pipeline
    import torch
    p = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=hf_token)
    if torch.cuda.is_available(): p.to(torch.device("cuda"))
    return p

def diarize(pipeline, wav_path, num_speakers=2):
    result = pipeline(wav_path, num_speakers=num_speakers)
    return [{"start":t.start,"end":t.end,"speaker":s} for t,_,s in result.itertracks(yield_label=True)]

def assign_speaker(whisper_segs, diar_segs):
    results=[]
    for ws in whisper_segs:
        best, overlap_best = "SPEAKER_00", 0
        for ds in diar_segs:
            overlap = max(0, min(ws["end"],ds["end"]) - max(ws["start"],ds["start"]))
            if overlap > overlap_best: overlap_best, best = overlap, ds["speaker"]
        results.append({**ws,"text":ws["text"].strip(),"speaker":best})
    return results

def group_by_speaker(assigned):
    grouped={}
    for s in assigned: grouped.setdefault(s["speaker"],[]).append(s)
    return grouped, {k:" ".join(x["text"] for x in v) for k,v in grouped.items()}

def format_time(sec):
    m,s = divmod(int(sec),60); return f"{m:02d}:{s:02d}"
