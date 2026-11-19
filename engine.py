"""Lazy OmniVoice adapter. The UI can start without downloading any weights."""

from pathlib import Path
from collections import OrderedDict
import tempfile
import threading
import time
import uuid

import soundfile as sf

from voice_core import Settings, join_audio, read_reference, split_text
from prompt_pack import MODEL_ID, MODEL_REVISION, audio_key, load_prompt


class VoiceEngine:
    def __init__(self, device: str = "auto", previous=None):
        if device not in {"auto", "cpu", "cuda", "mps"}:
            raise ValueError("Thiết bị không được hỗ trợ.")
        self.device = device
        self.model = getattr(previous, "model", None)
        self._lock = getattr(previous, "_lock", None) or threading.Lock()
        self._output = getattr(previous, "_output", None) or tempfile.TemporaryDirectory(prefix="vietvoice-")
        self._prompts = getattr(previous, "_prompts", OrderedDict())
        self._prompt_model = getattr(previous, "_prompt_model", None)
        self._saved_prompts = getattr(previous, "_saved_prompts", {})

    def use_prepared_library(self, library):
        self._saved_prompts = {entry["prompt_key"]: entry["prompt_path"] for entry in library
                               if entry.get("prompt_key") and entry.get("prompt_path")}

    @property
    def output_dir(self) -> str:
        return self._output.name

    def _load_model(self):
        if self.model is not None:
            return
        try:
            import torch
            from omnivoice import OmniVoice
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError("Chưa đủ thư viện AI. Hãy cài requirements.txt và PyTorch theo README.") from exc
        device = self.device
        if device == "auto":
            device = ("cuda" if torch.cuda.is_available() else
                      "mps" if torch.backends.mps.is_available() else "cpu")
        if device == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("Không tìm thấy CUDA. Hãy bật GPU trên Colab.")
            major, _ = torch.cuda.get_device_capability()
            if major < 7:
                raise RuntimeError("GPU này quá cũ. Hãy dùng Colab T4 hoặc chạy với --device cpu.")
        self.model = OmniVoice.from_pretrained(
            snapshot_download(MODEL_ID, revision=MODEL_REVISION),
            device_map=device,
            dtype=torch.float32 if device == "cpu" else torch.float16,
            load_asr=False,
            asr_device="cpu",
        )

    def _get_prompt(self, ref_audio, transcript, settings, report):
        import torch

        if self._prompt_model is not self.model:
            self._prompts.clear()
            self._prompt_model = self.model
        key = audio_key(ref_audio, transcript)
        if key in self._prompts:
            prompt = self._prompts[key]
            self._prompts.move_to_end(key)
            report(0.05, "Dùng giọng đã lưu — bỏ qua phân tích mẫu.")
            return prompt
        if key in self._saved_prompts:
            if MODEL_REVISION not in str(getattr(getattr(self.model, "config", None), "_name_or_path", "")):
                raise ValueError("Checkpoint mô hình khác gói prompt; khởi động lại phiên và chạy ô 1–3.")
            report(0.05, "Dùng prompt GitHub đã phân tích sẵn — không chạy Whisper.")
            prompt = load_prompt(self._saved_prompts[key])
        else:
            report(0.05, "Phân tích giọng lần đầu; kết quả sẽ được lưu trong phiên…")
            cuda_devices = ([torch.cuda.current_device()]
                            if str(self.model.device).startswith("cuda") else [])
            # Keep prompt preparation from shifting synthesis RNG on cache hits.
            with torch.random.fork_rng(devices=cuda_devices), torch.inference_mode():
                torch.manual_seed(int(settings.seed))
                prompt = self.model.create_voice_clone_prompt(
                    ref_audio=ref_audio, ref_text=transcript.strip() or None,
                )
        self._prompts[key] = prompt
        if len(self._prompts) > 200:
            self._prompts.popitem(last=False)
        return prompt

    def synthesize(self, text: str, reference: str, transcript: str,
                   settings: Settings, report=None) -> tuple[str, str]:
        report = report or (lambda value, message: None)
        settings.validate()
        chunks = split_text(text)
        if not isinstance(transcript, str) or len(transcript) > 2000:
            raise ValueError("Lời giọng mẫu tối đa 2.000 ký tự.")
        ref_audio = read_reference(reference)
        with self._lock:
            started = time.monotonic()
            report(0, "Đang chuẩn bị mô hình…" if self.model is not None else
                   "Đang tải mô hình; lần đầu cần tải trọng số từ Hugging Face…")
            self._load_model()
            # Injection of a fake model in tests exercises the full pipeline without GPU.
            import torch

            cuda_devices = ([torch.cuda.current_device()]
                            if str(self.model.device).startswith("cuda") else [])
            prompt = self._get_prompt(ref_audio, transcript, settings, report)
            random_context = torch.random.fork_rng(devices=cuda_devices)
            with random_context, torch.inference_mode():
                torch.manual_seed(int(settings.seed))
                if str(self.model.device).startswith("mps"):
                    torch.mps.manual_seed(int(settings.seed))
                audios = []
                for index, chunk in enumerate(chunks):
                    report(0.1 + 0.85 * index / len(chunks),
                           f"Đang đọc đoạn {index + 1}/{len(chunks)}…")
                    audios.append(self.model.generate(
                        text=chunk, language="vi", voice_clone_prompt=prompt,
                        speed=float(settings.speed), num_step=int(settings.steps),
                    )[0])
            rate = int(self.model.sampling_rate)
            waveform = join_audio(audios, rate, float(settings.pause))
            # Keep only this app's temporary exports for at most one hour.
            for old in Path(self.output_dir).glob("vietvoice-*.wav"):
                try:
                    if time.time() - old.stat().st_mtime > 3600:
                        old.unlink()
                except OSError:
                    pass
            output = Path(self.output_dir) / f"vietvoice-{uuid.uuid4().hex}.wav"
            sf.write(output, waveform, rate, subtype="PCM_16")
            elapsed = time.monotonic() - started
            report(1, "Hoàn tất")
            status = (f"Đã tạo {len(waveform) / rate:.1f} giây · {len(chunks)} đoạn · "
                      f"{rate:,} Hz · xử lý {elapsed:.1f} giây · seed {int(settings.seed)}")
            return str(output), status

    def close(self):
        self._prompts.clear()
        self._saved_prompts.clear()
        self._prompt_model = None
        self._output.cleanup()
