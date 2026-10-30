"""Two simulated people talk through the real SpeaKore server: John (English) and Lucía (Spanish).

Why: a phone's screen recording only captures what the phone plays, never your own voice while the app holds the
microphone. So to show both sides of a conversation, both people are simulated: their voices are pre-recorded WAV
files (in voices/), sent as audio to the live SpeaKore backend, which recognises, translates with NVIDIA Nemotron on
Nebius Token Factory, and speaks the translation back. Nothing here is mocked; only the speakers are simulated.

    street  two phones (P2P): John and Lucía each connect as their own phone
    table   one phone in the middle, two seats

Usage:
    pip install httpx websockets numpy
    export SPEAKORE_API=...                  # server address and code: judges receive both privately
    export SPEAKORE_JURY_CODE=...
    python simulate_conversation.py street   # writes street.wav + street.srt
    python simulate_conversation.py table

Output: one WAV with each original sentence followed by the translation the other person heard, plus subtitles.
"""
import asyncio
import json
import os
import sys
import time
import wave
from pathlib import Path

import httpx
import numpy as np
from websockets.asyncio.client import connect

API = os.environ.get("SPEAKORE_API", "")
WS = API.replace("https://", "wss://").replace("http://", "ws://")
CODE = os.environ.get("SPEAKORE_JURY_CODE", "")
VOICES = Path(__file__).parent / "voices"
OUT_RATE = 24000  # the server speaks 16-bit PCM at 24 kHz
FRAME = 3200  # 0.1 s of 16 kHz 16-bit audio

SCRIPTS = {
    "street": [
        ("john", "street_1_john", "Hi! Excuse me, do you know where the train station is?"),
        ("lucia", "street_2_lucia", "¡Hola! Sí, claro. La estación de tren está muy cerca, a cinco minutos andando."),
        ("john", "street_3_john", "Great, how do I get there?"),
        ("lucia", "street_4_lucia", "Sigue recto por esta calle y gira a la izquierda en la plaza."),
        ("john", "street_5_john", "Thanks! When does the next train to Málaga leave?"),
        ("lucia", "street_6_lucia", "El próximo tren a Málaga sale a las cuatro y media. ¡Buen viaje!"),
    ],
    "table": [
        ("john", "table_1_john", "Shall we play one more round before dinner?"),
        ("lucia", "table_2_lucia", "Sí, claro, pero la cena es a las nueve y media."),
        ("john", "table_3_john", "Perfect. Lucía, it is your turn to shuffle the cards."),
        ("lucia", "table_4_lucia", "Vale, pero esta vez no me ganas, te lo prometo."),
    ],
}
PEOPLE = {"john": ("John", "en", "male"), "lucia": ("Lucía", "es", "female")}


def read_voice(name: str) -> bytes:
    with wave.open(str(VOICES / f"{name}.wav")) as w:
        return w.readframes(w.getnframes())


def to_out_rate(pcm16k: bytes) -> np.ndarray:
    x = np.frombuffer(pcm16k, dtype=np.int16).astype(np.float32)
    t = np.linspace(0, len(x) - 1, int(len(x) * OUT_RATE / 16000))
    return np.interp(t, np.arange(len(x)), x).astype(np.int16)


TOKENS = Path(__file__).parent / ".tokens.json"  # local only (gitignored): reuse sessions, don't create new accounts


def login(name: str) -> str:
    saved = json.loads(TOKENS.read_text()) if TOKENS.exists() else {}
    if name in saved:
        r = httpx.post(f"{API}/auth/refresh", json={"refreshToken": saved[name]}, timeout=30)
        if r.status_code != 200:
            saved.pop(name)
    if name not in saved:
        r = httpx.post(f"{API}/auth/jury", json={"code": CODE, "name": name}, timeout=30)
        r.raise_for_status()
    data = r.json()
    saved[name] = data["refreshToken"]  # refresh tokens rotate: always keep the newest one
    fd = os.open(TOKENS, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # owner-only: these are credentials
    with os.fdopen(fd, "w") as f:
        json.dump(saved, f)
    os.chmod(TOKENS, 0o600)
    return data["token"]


async def send_speech(ws, pcm: bytes) -> float:
    for i in range(0, len(pcm), FRAME):  # real time, like a microphone
        await ws.send(pcm[i : i + FRAME])
        await asyncio.sleep(0.1)
    for _ in range(20):  # 2 s of silence: end of the sentence
        await ws.send(b"\x00" * FRAME)
        await asyncio.sleep(0.1)
    return time.monotonic() - 2.0


async def collect(ws, is_translation, timeout: float = 20.0, quiet: float = 1.5) -> tuple[str, bytes, float | None]:
    """Read until the translation text arrived and the spoken translation has finished."""
    text, audio, first_audio = "", bytearray(), None
    start, last = time.monotonic(), None
    while time.monotonic() - start < timeout:
        wait = quiet if (text and last) else timeout
        try:
            m = await asyncio.wait_for(ws.recv(), wait)
        except asyncio.TimeoutError:
            if text:
                break
            continue
        if isinstance(m, bytes):
            audio += m
            last = time.monotonic()
            first_audio = first_audio or last
        else:
            e = json.loads(m)
            if is_translation(e):
                text = e.get("text") or " / ".join((e.get("translations") or {}).values())
    return text, bytes(audio), first_audio


async def street(turns) -> list:
    socks = {}
    for key, (name, lang, voice) in PEOPLE.items():
        # The speaking phone doesn't read its own events during a turn: a large queue keeps the connection alive.
        ws = await connect(f"{WS}/live/p2p?token={login(name)}", max_queue=4096, ping_interval=None)
        await ws.send(json.dumps({"type": "start", "pipeline": "p2p", "sourceLang": lang, "name": name, "voice": voice}))
        socks[key] = ws
    codes = {}
    for key, ws in socks.items():
        while key not in codes:
            e = json.loads(await ws.recv())
            if e["type"] == "ready":
                codes[key] = e["code"]
    await socks["john"].send(json.dumps({"type": "invite", "code": codes["lucia"]}))
    paired = set()
    while len(paired) < 2:
        for key, ws in socks.items():
            try:
                e = json.loads(await asyncio.wait_for(ws.recv(), 0.5))
            except asyncio.TimeoutError:
                continue
            if e["type"] == "p2p_invite":
                await ws.send(json.dumps({"type": "answer", "inviteId": e["inviteId"], "accept": True}))
            elif e["type"] == "p2p_paired":
                paired.add(key)
    results = []
    for who, voice, line in turns:
        listener = "lucia" if who == "john" else "john"
        pcm = read_voice(voice)
        sent, (text, audio, first) = await asyncio.gather(
            send_speech(socks[who], pcm),
            collect(socks[listener], lambda e: e.get("type") == "translation" and e.get("who") == "peer"),
        )
        results.append((who, line, pcm, text, audio, (first - sent) if first else None))
        print(f"{PEOPLE[who][0]}: {line}\n   -> {PEOPLE[listener][0]} hears: {text}  ({(first - sent):.2f} s)" if first else f"{PEOPLE[who][0]}: {line}\n   -> {text}")
    for ws in socks.values():
        await ws.close()
    return results


async def table(turns) -> list:
    async with connect(f"{WS}/live/group?token={login('Table')}") as ws:
        seats = [{"id": k, "lang": lang, "name": name} for k, (name, lang, _) in PEOPLE.items()]
        await ws.send(json.dumps({"type": "start", "pipeline": "group", "seats": seats}))
        assert json.loads(await ws.recv())["type"] == "ready"
        results = []
        for who, voice, line in turns:
            pcm = read_voice(voice)
            await ws.send(json.dumps({"type": "turn", "seat": who}))
            for i in range(0, len(pcm), FRAME):
                await ws.send(pcm[i : i + FRAME])
                await asyncio.sleep(0.1)
            sent = time.monotonic()
            await ws.send(json.dumps({"type": "end_turn"}))
            text, audio, first = await collect(ws, lambda e: e.get("type") == "group_translation")
            results.append((who, line, pcm, text, audio, (first - sent) if first else None))
            print(f"{PEOPLE[who][0]}: {line}\n   -> {text}" + (f"  ({first - sent:.2f} s)" if first else ""))
        return results


def srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write(mode: str, results: list) -> None:
    gap = np.zeros(int(OUT_RATE * 0.4), dtype=np.int16)
    track, subs, t = [], [], 0.0
    for who, line, pcm, text, audio, _latency in results:
        for label, chunk, words in ((PEOPLE[who][0], to_out_rate(pcm), line), ("SpeaKore", np.frombuffer(audio, dtype=np.int16), text)):
            if not len(chunk):
                continue
            dur = len(chunk) / OUT_RATE
            subs.append(f"{len(subs) + 1}\n{srt_time(t)} --> {srt_time(t + dur)}\n{label}: {words}\n")
            track += [chunk, gap]
            t += dur + len(gap) / OUT_RATE
    with wave.open(f"{mode}.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_RATE)
        w.writeframes(np.concatenate(track).tobytes())
    Path(f"{mode}.srt").write_text("\n".join(subs), encoding="utf-8")
    print(f"\nWrote {mode}.wav ({t:.0f} s) and {mode}.srt")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "street"
    if mode not in SCRIPTS or not CODE or not API:
        sys.exit("Usage: SPEAKORE_API=... SPEAKORE_JURY_CODE=... python simulate_conversation.py street|table")
    run = street if mode == "street" else table
    write(mode, asyncio.run(run(SCRIPTS[mode])))
