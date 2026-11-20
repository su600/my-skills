#!/usr/bin/env python3
"""音频转写 -> <outdir>/<base>.json + <outdir>/<base>.txt

用法:
  python3 asr.py <audio.mp3> <outdir> [base] [--prompt "领域提示词"]

输出:
  <outdir>/<base>.json  {"audio","duration","segments":[{start,end,text}]}
  <outdir>/<base>.txt   [MM:SS] 文本  逐行

实测速度: 2 vCPU / int8 / small / beam=1 约 3.3x 实时。
"""
import json
import os
import sys
import time

from faster_whisper import WhisperModel

MODEL_DIR = "/root/.cache/fw"
DEFAULT_PROMPT = "以下是中文大学课堂讲解。"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    audio, outdir = sys.argv[1], sys.argv[2]
    rest = [a for a in sys.argv[3:] if not a.startswith("--")]
    base = rest[0] if rest else os.path.splitext(os.path.basename(audio))[0]
    prompt = DEFAULT_PROMPT
    if "--prompt" in sys.argv:
        prompt = sys.argv[sys.argv.index("--prompt") + 1]

    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    model = WhisperModel("small", device="cpu", compute_type="int8",
                         cpu_threads=2, download_root=MODEL_DIR)
    print(f"[asr] model loaded {time.time()-t0:.1f}s", flush=True)

    segs, info = model.transcribe(
        audio, language="zh", vad_filter=True, beam_size=1,
        initial_prompt=prompt, condition_on_previous_text=False,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    total = info.duration
    rows = []
    t1 = time.time()
    for s in segs:
        rows.append({"start": round(s.start, 2), "end": round(s.end, 2),
                     "text": s.text.strip()})
        if len(rows) % 20 == 0:
            pct = s.end / total * 100 if total else 0
            print(f"[asr] {pct:5.1f}%  {s.end/60:.1f}/{total/60:.1f}min  "
                  f"elapsed {time.time()-t1:.0f}s", flush=True)

    with open(os.path.join(outdir, f"{base}.json"), "w", encoding="utf-8") as f:
        json.dump({"audio": audio, "duration": total, "segments": rows},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, f"{base}.txt"), "w", encoding="utf-8") as f:
        for r in rows:
            m, sec = divmod(int(r["start"]), 60)
            f.write(f"[{m:02d}:{sec:02d}] {r['text']}\n")
    dt = time.time() - t1
    print(f"[asr] done {len(rows)} segments in {dt:.0f}s "
          f"({total/dt:.1f}x realtime)", flush=True)


if __name__ == "__main__":
    main()
