"""Validation and audio processing; usable without PyTorch or model weights."""

from dataclasses import dataclass
from pathlib import Path
import math
import re
import unicodedata

import numpy as np
import soundfile as sf

MAX_TEXT = 4000
MAX_UPLOAD = 20 * 1024 * 1024
CHUNK_SIZE = 350
MAX_CHUNKS = 30


@dataclass(frozen=True)
class Settings:
    speed: float = 1.0
    steps: int = 32
    pause: float = 0.35
    seed: int = 42

    def validate(self):
        for name, value, low, high, integer in (
            ("Tốc độ", self.speed, 0.7, 1.3, False),
            ("Số bước", self.steps, 8, 64, True),
            ("Khoảng nghỉ", self.pause, 0, 1.5, False),
            ("Seed", self.seed, 0, 2**32 - 1, True),
        ):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not low <= value <= high
                    or (integer and value != int(value))):
                raise ValueError(f"{name} phải nằm trong khoảng {low}–{high}"
                                 + (" và là số nguyên." if integer else "."))


def split_text(text: str, limit: int = CHUNK_SIZE) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Hãy nhập văn bản cần đọc.")
    if len(text) > MAX_TEXT:
        raise ValueError(f"Mỗi lần tối đa {MAX_TEXT:,} ký tự.")
    if not isinstance(limit, int) or limit < 20:
        raise ValueError("Giới hạn đoạn phải là số nguyên từ 20 trở lên.")
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    if any(unicodedata.category(c) == "Cc" and c not in "\n\t" for c in text):
        raise ValueError("Văn bản có ký tự điều khiển không hợp lệ.")
    chunks = []
    # Split paragraphs first, then prefer punctuation or word boundaries.
    for paragraph in re.split(r"\n\s*\n", text):
        remaining = " ".join(paragraph.split())
        while len(remaining) > limit:
            window = remaining[:limit + 1]
            stops = list(re.finditer(r"[.!?;…](?:[\"'”’])?\s+", window))
            end = stops[-1].start() + len(stops[-1].group().rstrip()) if stops else 0
            if end < limit // 3:
                end = window.rfind(" ", 0, limit + 1)
            if end <= 0:
                end = limit
            chunks.append(remaining[:end].strip())
            remaining = remaining[end:].lstrip()
        if remaining:
            chunks.append(remaining)
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"Tối đa {MAX_CHUNKS} đoạn mỗi lần; hãy gộp bớt dòng trống.")
    return chunks


def read_reference(filename: str) -> tuple[np.ndarray, int]:
    if not filename:
        raise ValueError("Hãy tải lên một đoạn giọng mẫu của bạn.")
    path = Path(filename)
    if not path.is_file() or path.stat().st_size > MAX_UPLOAD:
        raise ValueError("Tệp giọng mẫu không tồn tại hoặc lớn hơn 20 MB.")
    try:
        with sf.SoundFile(path) as source:
            if source.format not in {"WAV", "WAVEX", "RF64", "FLAC", "OGG", "MP3"}:
                raise ValueError("Chỉ hỗ trợ WAV, MP3, FLAC hoặc OGG.")
            rate = source.samplerate
            if not 8000 <= rate <= 192000 or source.channels not in (1, 2):
                raise ValueError("Giọng mẫu cần mono/stereo, tần số 8–192 kHz.")
            if not 3 <= len(source) / rate <= 20:
                raise ValueError("Giọng mẫu cần dài 3–20 giây; nên dùng 3–10 giây.")
            samples = source.read(dtype="float32", always_2d=True)
    except (RuntimeError, OSError) as exc:
        raise ValueError("Không đọc được âm thanh. Hãy thử xuất lại thành WAV.") from exc
    if not np.isfinite(samples).all():
        raise ValueError("Âm thanh chứa dữ liệu không hợp lệ.")
    mono = samples.mean(axis=1)
    if float(np.sqrt(np.mean(mono**2))) < 1e-5:
        raise ValueError("Giọng mẫu quá nhỏ hoặc chỉ có im lặng.")
    return mono[np.newaxis, :], rate


def join_audio(chunks: list[np.ndarray], rate: int, pause: float) -> np.ndarray:
    if not chunks or not isinstance(rate, int) or not 8000 <= rate <= 192000:
        raise ValueError("Không có âm thanh hợp lệ để xuất.")
    if not math.isfinite(pause) or not 0 <= pause <= 1.5:
        raise ValueError("Khoảng nghỉ không hợp lệ.")
    result = []
    gap = np.zeros(round(rate * pause), dtype=np.float32)
    for i, chunk in enumerate(chunks):
        audio = np.array(chunk, dtype=np.float32, copy=True)
        if (audio.ndim != 1 or not 0 < audio.size <= rate * 120
                or not np.isfinite(audio).all()):
            raise ValueError("Mô hình trả về âm thanh không hợp lệ.")
        fade = min(round(rate * 0.005), audio.size // 2)
        if fade:
            ramp = np.linspace(0, 1, fade, dtype=np.float32)
            audio[:fade] *= ramp
            audio[-fade:] *= ramp[::-1]
        if i:
            result.append(gap)
        result.append(audio)
    joined = np.concatenate(result)
    peak = float(np.max(np.abs(joined)))
    if peak < 1e-6:
        raise ValueError("Mô hình chỉ tạo im lặng. Hãy thử giọng mẫu khác.")
    if peak > 1:
        joined *= 0.98 / peak
    return joined
