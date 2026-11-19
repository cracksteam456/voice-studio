"""Build the self-contained, native Google Colab notebook."""

import hashlib
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, source):
    source = textwrap.dedent(source).strip() + "\n"
    result = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True),
              "id": hashlib.sha256(source.encode()).hexdigest()[:12]}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def build():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    files = {name: (ROOT / name).read_text(encoding="utf-8")
             for name in ("voice_core.py", "engine.py", "colab_ui.py", "reference_library.py")}
    setup = '''
        #@title 1. Cài thư viện (chạy một lần trên phiên mới)
        import importlib.metadata as metadata
        import importlib.util
        import subprocess
        import sys
        from pathlib import Path

        if importlib.util.find_spec("google.colab") is None:
            raise RuntimeError("Notebook này dành cho Google Colab. Hãy mở bằng colab.research.google.com.")
        try:
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                 capture_output=True, text=True, check=False)
        except FileNotFoundError:
            gpu = None
        if gpu is None or gpu.returncode:
            raise RuntimeError("Hãy bật GPU: Runtime → Change runtime type → T4 GPU, rồi chạy lại.")
        print("GPU:", gpu.stdout.strip())

        # Cài bằng pip của đúng kernel; không thực thi script tải về từ URL.
        wanted = "2.8.0"
        try:
            torch_ok = (all(metadata.version(name).split("+")[0] == wanted
                            for name in ("torch", "torchaudio"))
                        and metadata.version("torchvision").split("+")[0] == "0.23.0")
        except metadata.PackageNotFoundError:
            torch_ok = False
        if not torch_ok:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--only-binary=:all:",
                "torch==2.8.0", "torchaudio==2.8.0", "torchvision==0.23.0",
                "--index-url", "https://download.pytorch.org/whl/cu128",
            ])
        Path("vietvoice-requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "vietvoice-requirements.txt"
        ])
        # Colab's preinstalled TorchCodec may target a different PyTorch ABI.
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--only-binary=:all:", "--no-deps",
            "--force-reinstall", "torchcodec==0.7.0",
            "--index-url", "https://download.pytorch.org/whl/cpu",
        ])
        codec_probe = subprocess.run(
            [sys.executable, "-c", "from torchcodec.decoders import AudioDecoder"],
            capture_output=True, text=True,
        )
        if codec_probe.returncode:
            raise RuntimeError("TorchCodec chưa khớp PyTorch. Khởi động lại phiên rồi chạy lại ô 1.")
        print("Đã cài xong. Nếu Colab yêu cầu khởi động lại phiên, khởi động lại rồi chạy ô 2 và 3.")
    '''
    setup = "REQUIREMENTS = " + repr(requirements) + "\n" + textwrap.dedent(setup).strip()
    extract = (
        "#@title 2. Chuẩn bị VietVoice Studio và kiểm tra GPU\n"
        "from pathlib import Path\nimport sys\nimport importlib\nimport os\n\n"
        "os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'\n"
        "PROJECT = Path('/content/vietvoice-studio')\n"
        "PROJECT.mkdir(parents=True, exist_ok=True)\n"
        f"FILES = {files!r}\n"
        "for name, content in FILES.items():\n"
        "    (PROJECT / name).write_text(content, encoding='utf-8')\n"
        "if str(PROJECT) not in sys.path:\n"
        "    sys.path.insert(0, str(PROJECT))\n"
        "importlib.invalidate_caches()\n"
        "import torch\n"
        "from omnivoice import OmniVoice\n"
        "from transformers import AutoFeatureExtractor\n"
        "import voice_core, engine, reference_library\n"
        "for module in (voice_core, engine, reference_library):\n"
        "    importlib.reload(module)\n"
        "from engine import VoiceEngine\n"
        "from reference_library import load_library\n"
        "if not torch.cuda.is_available():\n"
        "    raise RuntimeError('Chưa có GPU. Chọn Runtime → Change runtime type → T4 GPU.')\n"
        "if 'voice_engine' not in globals():\n"
        "    voice_engine = VoiceEngine('cuda')\n"
        "voice_library = load_library()\n"
        "print('GPU:', torch.cuda.get_device_name(0))\n"
        "print('Sẵn sàng. Trọng số sẽ tải khi bạn tạo giọng lần đầu.')\n"
    )
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
            "colab": {"gpuType": "T4", "provenance": []},
        },
        "cells": [
            cell("markdown", '''
                # VietVoice Studio
                **Văn bản của bạn. Giọng nói của bạn.**

                Tạo tiếng nói từ giọng mẫu của bạn **ngay trong Google Colab**.
                Notebook chứa sẵn mã nguồn, không cần cài gì trên máy, không cần liên kết Gradio hay đăng nhập phụ.

                1. Chọn **Runtime → Change runtime type → T4 GPU** (nếu khả dụng).
                2. Chạy lần lượt **3 ô mã** bên dưới.
                3. Bộ giọng có sẵn tự tải từ GitHub trong ô 2; chọn giọng ở ô 3 rồi nhập nội dung.
                4. Bấm **Tạo giọng nói**, nghe trong notebook và bấm **Tải WAV**.

                Cần Internet để cài thư viện/tải trọng số. Không cam kết thời gian tạo vì tùy GPU và độ dài.
                Văn bản và âm thanh được tải lên và xử lý trong phiên Colab của bạn.
                Tải bản đọc về trước khi xóa/ngắt phiên. Chưa có bước huấn luyện mô hình mới.
                **158 mẫu**: 8 giọng ban đầu + 50 tiếng Việt + 50 thịnh hành toàn cầu + 50 dùng nhiều toàn cầu.
                Bộ giọng tự tải từ kho công khai **cracksteam456/voice-studio** mỗi phiên;
                không cần GitHub token hoặc tải giọng mẫu từ máy lên.
                Dùng giọng của bạn hoặc giọng được chủ sở hữu cho phép sử dụng.
            '''),
            cell("markdown", "## 1. Cài thư viện\nChạy trên một phiên Colab mới để tránh xung đột thư viện đã nạp."),
            cell("code", setup),
            cell("markdown", "## 2. Chuẩn bị ứng dụng và tải giọng từ GitHub\nMỗi lần chạy ô này sẽ lấy bộ mẫu hiện tại từ GitHub Release và kiểm tra checksum. Chưa tải trọng số mô hình."),
            cell("code", extract),
            cell("markdown", '''
                ## 3. Tạo giọng ngay tại đây
                Chọn giọng có sẵn, nhập nội dung rồi bấm **Tạo giọng nói**.
                Dùng **Nhóm giọng** để lọc đủ 158 mẫu.
                Hoặc chọn **Giọng tải lên của tôi** để dùng mẫu riêng **2–20 giây**.
                Bạn có thể sửa nội dung và bấm tạo nhiều lần mà không cần chạy lại ô cài đặt.
                **16 bước** để thử nhanh; **32 bước** là mặc định. Tối đa **4.000 ký tự/lần**.
                Lần tạo đầu tiên sẽ tải trọng số từ Hugging Face.
            '''),
            cell("code", '''
                #@title 3. Mở giao diện VietVoice Studio
                from google.colab import output
                from IPython.display import display
                import importlib
                import colab_ui
                importlib.reload(colab_ui)
                from colab_ui import build_ui

                output.enable_custom_widget_manager()
                if 'panel' in globals():
                    panel.close()
                panel = build_ui(voice_engine, voice_library)
                display(panel)
            '''),
            cell("markdown", '''
                ## Mẹo và xử lý sự cố
                - **Hết bộ nhớ GPU:** giảm số bước xuống 16, dùng mẫu ngắn, chia nội dung; khởi động lại phiên nếu cần.
                - **Tải mô hình lâu:** lần đầu cần tải trọng số; xem thông báo tiến trình ở ô 3.
                - **Giọng chưa giống:** dùng mẫu rõ, một người nói, không nhạc nền; chép lời mẫu thật chính xác.
                - **Số và chữ viết tắt đọc chưa đúng:** viết thành cách đọc mong muốn trước khi tạo.
                - **Lời mẫu để trống:** ứng dụng tải thêm Whisper để nhận dạng trên CPU; sẽ chậm hơn.
                - **Giao diện không hiện:** chạy lại ô 3 sau khi ô 1 và 2 đã thành công.
                - **Xóa dữ liệu:** tải WAV về rồi chọn **Runtime → Disconnect and delete runtime**.
                  Không chia sẻ notebook kèm đầu ra hoặc giọng mẫu nếu có thông tin riêng tư.
                - **Đổi mã nguồn:** sửa các tệp Python rồi chạy `python scripts/build_notebook.py` để dựng lại notebook.

                Tham khảo notebook của [doanquangkien/voice-notebooks](https://github.com/doanquangkien/voice-notebooks).
                Mã ứng dụng được viết riêng, không kèm giọng thu của tác giả nguồn.
                Dùng thư viện [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), Apache-2.0;
                mô hình và các phụ thuộc giữ giấy phép riêng, xem tài liệu upstream.
            '''),
        ],
    }
    target = ROOT / "VietVoice_Studio_Colab.ipynb"
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Created {target.name}: {len(notebook['cells'])} cells")
    return notebook


if __name__ == "__main__":
    build()
