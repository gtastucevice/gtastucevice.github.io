#!/usr/bin/env python3
"""Intros face caméra de Roméo : découpe une phrase d'une vidéo verticale (iPhone), format 1080x1920 30 i/s,
volume égalisé, sous-titres synchronisés (mot dit en jaune, comme la voix off) et petit bandeau « ROMÉO · GTASTUCE VICE ».
Usage :
  python3 outils/intro_romeo.py clip  <video.MOV> <debut_s> <fin_s> <mots.json> <sortie.mp4>
      mots.json : [["Arrête", 6.1, 6.4], ["tout.", 6.4, 6.7], ...]  (secondes, temps de la vidéo source)
  python3 outils/intro_romeo.py joindre <intro.mp4> <video_du_jour.mp4> <sortie.mp4> [fin.mp4]
Les vidéos source de Roméo et les intros découpées restent sur le Drive (dossier « GTASTUCE VICE / Intros Roméo »), jamais dans le dépôt."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "fonts")

def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def make_ass(words, t0, t1, path):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Sub,Archivo Black,78,&H00FFFFFF,&H00FFFFFF,&H00331A0B,&H96000000,0,0,0,0,100,100,0,0,1,6,3,2,70,70,430,1\n"
            "Style: Tag,Archivo Black,40,&H00FFFFFF,&H00FFFFFF,&H00331A0B,&H96000000,0,0,0,0,100,100,1,0,1,4,0,8,60,60,110,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(t1 - t0)},Tag,,0,0,0,,{{\\c&H5CE4FF&}}ROMÉO{{\\c&HFFFFFF&}} · GTASTUCE VICE"]
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[0].endswith((".", "?", "!", ",")):
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for ci, ch in enumerate(chunks):
        end_chunk = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else t1
        for wi, w in enumerate(ch):
            a = w[1]; b = ch[wi + 1][1] if wi + 1 < len(ch) else end_chunk
            txt = " ".join((("{\\c&H5CE4FF&}" + x[0].upper() + "{\\c&HFFFFFF&}") if j == wi else x[0].upper()) for j, x in enumerate(ch))
            ev.append(f"Dialogue: 0,{ass_time(a - t0)},{ass_time(b - t0)},Sub,,0,0,0,,{txt}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")

def clip(src, t0, t1, words_json, out):
    t0, t1 = float(t0), float(t1); words = json.load(open(words_json, encoding="utf-8"))
    d = t1 - t0
    with tempfile.TemporaryDirectory() as tmp:
        ass = os.path.join(tmp, "s.ass"); make_ass(words, t0, t1, ass)
        vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.08,"
              f"ass={ass}:fontsdir={FONTS},fade=t=in:st=0:d=0.12,fade=t=out:st={d - 0.15:.2f}:d=0.15")
        af = f"loudnorm=I=-14:TP=-1.5,aresample=44100,afade=t=in:st=0:d=0.05,afade=t=out:st={d - 0.15:.2f}:d=0.15"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(d), "-i", src, "-vf", vf, "-af", af, "-ac", "2",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", out], check=True)

def joindre(intro, video, out, fin=None):
    ins = [intro, video] + ([fin] if fin else [])
    args = sum([["-i", x] for x in ins], [])
    n = len(ins); fc = "".join(f"[{i}:v]fps=30,scale=1080:1920,setsar=1[v{i}];[{i}:a]aresample=44100,aformat=channel_layouts=stereo[a{i}];" for i in range(n))
    fc += "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "clip": clip(*sys.argv[2:7])
    elif sys.argv[1] == "joindre": joindre(*sys.argv[2:])
