"""Native notebook controls: no web server, tunnel or separate login."""

from pathlib import Path
import tempfile

import ipywidgets as widgets
from IPython.display import Audio, display

from engine import VoiceEngine
from voice_core import MAX_TEXT, MAX_UPLOAD, Settings, split_text

EXAMPLE = (
    "Xin chào, đây là VietVoice Studio. Biến ý tưởng thành lời nói bằng chính giọng của bạn.\n\n"
    "Bạn có thể dùng bản thu để thuyết minh video, kể chuyện hoặc đọc nội dung mình yêu thích."
)


def build_ui(engine=None, library=None):
    engine = engine or VoiceEngine("cuda")
    library = library or []
    reference_dir = tempfile.TemporaryDirectory(prefix="vietvoice-reference-")
    last_output = {"path": None}
    full = widgets.Layout(width="100%")
    text = widgets.Textarea(value=EXAMPLE, description="Văn bản", placeholder="Nhập văn bản tiếng Việt…",
                            layout=widgets.Layout(width="100%", height="180px"))
    reference = widgets.FileUpload(accept=".wav,.mp3,.flac,.ogg", multiple=False,
                                   description="Tải giọng mẫu", layout=widgets.Layout(width="200px"))
    voice = widgets.Dropdown(
        options=[("Giọng tải lên của tôi", "")] + [(entry["name"], entry["path"]) for entry in library],
        value=library[0]["path"] if library else "", description="Chọn giọng", layout=full,
    )
    preview = widgets.Output(layout=full)
    transcript = widgets.Textarea(description="Lời mẫu", placeholder="Chép đúng lời nói trong giọng mẫu; có thể để trống.",
                                  layout=widgets.Layout(width="100%", height="85px"))
    speed = widgets.FloatSlider(value=1, min=0.7, max=1.3, step=0.05,
                                description="Tốc độ", readout_format=".2f", layout=full)
    steps = widgets.IntSlider(value=32, min=8, max=64, description="Số bước", layout=full)
    pause = widgets.FloatSlider(value=0.35, min=0, max=1.5, step=0.05,
                                description="Nghỉ (giây)", readout_format=".2f", layout=full)
    seed = widgets.BoundedIntText(value=42, min=0, max=2**32-1, description="Seed")
    options = widgets.VBox([
        widgets.HTML("<b>Điều chỉnh bản đọc</b>"), speed, steps, pause, seed,
    ], layout=full)
    summary = widgets.Label()
    status = widgets.Label("Sẵn sàng. Mô hình sẽ tải khi bạn bấm tạo lần đầu.")
    progress = widgets.FloatProgress(value=0, min=0, max=1, description="Tiến trình", layout=full)
    create = widgets.Button(description="Tạo giọng nói", button_style="success", icon="play")
    download = widgets.Button(description="Tải WAV", icon="download", disabled=True)
    output = widgets.Output(layout=full)

    def update_summary(change=None):
        try:
            summary.value = f"{len(text.value):,}/{MAX_TEXT:,} ký tự · {len(split_text(text.value))} đoạn"
        except ValueError as exc:
            summary.value = str(exc)

    def report(value, message):
        progress.value = value
        status.value = message

    def change_voice(change=None):
        preview.clear_output(wait=True)
        selected = next((entry for entry in library if entry["path"] == voice.value), None)
        transcript.value = selected.get("transcript", "") if selected else ""
        reference.disabled = bool(selected)
        if selected:
            with preview:
                display(Audio(filename=selected["path"]))

    def generate(_):
        create.disabled = True
        download.disabled = True
        last_output["path"] = None
        progress.value = 0
        progress.bar_style = "info"
        output.clear_output(wait=True)
        try:
            temporary = not bool(voice.value)
            if temporary:
                if len(reference.value) != 1:
                    raise ValueError("Hãy chọn giọng có sẵn hoặc tải lên đúng một tệp giọng mẫu.")
                item = next(iter(reference.value.values())) if isinstance(reference.value, dict) else reference.value[0]
                content = item["content"]
                if not 0 < len(content) <= MAX_UPLOAD:
                    raise ValueError("Giọng mẫu cần nhỏ hơn hoặc bằng 20 MB.")
                # Never derive a filesystem path from an uploaded filename.
                reference_path = Path(reference_dir.name) / "reference.audio"
                reference_path.write_bytes(bytes(content))
            else:
                if voice.value not in {entry["path"] for entry in library}:
                    raise ValueError("Giọng đã chọn không nằm trong danh sách.")
                reference_path = Path(voice.value)
            try:
                path, message = engine.synthesize(
                    text.value, str(reference_path), transcript.value,
                    Settings(speed.value, steps.value, pause.value, seed.value), report=report,
                )
            finally:
                if temporary:
                    reference_path.unlink(missing_ok=True)
            with output:
                display(Audio(filename=path))
                print(message)
            last_output["path"] = path
            download.disabled = False
            status.value = "Hoàn tất. Nghe bên dưới hoặc bấm Tải WAV."
            progress.bar_style = "success"
        except ValueError as exc:
            status.value = str(exc)
            progress.bar_style = "danger"
            with output:
                print(str(exc))
        except Exception as exc:
            status.value = "Chưa tạo được giọng. Kiểm tra kết nối tải mô hình và bộ nhớ GPU."
            progress.bar_style = "danger"
            with output:
                print(status.value, f"Loại lỗi: {type(exc).__name__}.")
                print("Nếu hết bộ nhớ, khởi động lại phiên và thử nội dung ngắn hơn.")
        finally:
            create.disabled = False

    def save(_):
        path = last_output["path"]
        if path and Path(path).is_file():
            from google.colab import files
            files.download(path)
        else:
            status.value = "Bản WAV không còn trong phiên. Hãy tạo lại."
            download.disabled = True

    text.observe(update_summary, names="value")
    voice.observe(change_voice, names="value")
    create.on_click(generate)
    download.on_click(save)
    update_summary()
    change_voice()
    panel = widgets.VBox([
        widgets.HTML("<h2>1. Văn bản cần đọc</h2>"), text, summary,
        widgets.HTML("<h2>2. Giọng mẫu của bạn</h2><p>Chọn một tệp WAV, MP3, FLAC hoặc OGG, "
                     "tối đa 20 MB. Nên dùng 3–10 giây, rõ tiếng, một người nói.</p>"),
        voice, preview, reference,
        widgets.HTML("<b>Lời nói trong giọng mẫu</b><p>Điền chính xác để tránh tải thêm Whisper. "
                     "Để trống sẽ nhận dạng trên CPU và chậm hơn.</p>"),
        transcript, options, widgets.HBox([create, download]), progress, status,
        widgets.HTML("<h2>3. Bản đọc của bạn</h2>"), output,
    ], layout=full)
    # Hold references until the displayed panel is released by the notebook.
    panel._vietvoice_resources = (engine, reference_dir)
    return panel
