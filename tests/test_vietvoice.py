import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from voice_core import Settings, join_audio, read_reference, split_text

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def test_split_preserves_vietnamese_and_paragraphs(self):
        text = "Xin chào Việt Nam! Đây là giọng nói của tôi.\n\nĐoạn tiếp theo rất rõ."
        parts = split_text(text, 30)
        self.assertTrue(all(0 < len(part) <= 30 for part in parts))
        self.assertEqual(" ".join(parts), " ".join(text.split()))

    def test_split_long_unbroken_word(self):
        self.assertEqual(split_text("x" * 101, 40), ["x" * 40, "x" * 40, "x" * 21])

    def test_unicode_and_windows_newlines(self):
        self.assertEqual(split_text("Vie\u0323\u0302t Nam\r\n\r\nXin chào"), ["Việt Nam", "Xin chào"])

    def test_reject_empty_huge_or_control_text(self):
        for text in ["", " \n\t", "x" * 4001, "abc\x00def", "a\n\n" * 31]:
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                split_text(text)

    def test_settings_reject_invalid_values(self):
        Settings().validate()
        for settings in [Settings(speed=float("nan")), Settings(steps=8.5), Settings(seed=-1),
                         Settings(pause=float("inf")), Settings(speed=True), Settings(seed=2**32)]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                settings.validate()

    def test_join_pause_peak_and_no_trailing_gap(self):
        a = np.ones(800, dtype=np.float32) * 2
        out = join_audio([a, a], 8000, 0.2)
        self.assertEqual(out.shape, (3200,))
        self.assertTrue(np.all(out[800:2400] == 0))
        self.assertLessEqual(float(np.max(np.abs(out))), 1)
        self.assertEqual(a[0], 2)  # Caller data stays untouched.
        for chunks in [[], [np.array([float("nan")])], [np.zeros(10)], [np.zeros((2, 3))]]:
            with self.assertRaises(ValueError):
                join_audio(chunks, 8000, 0)

    def test_reference_file_content_and_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "ref.wav"
            wave = np.sin(np.arange(4 * 16000) * (2 * np.pi * 220 / 16000)) * 0.2
            sf.write(filename, np.stack([wave, wave], axis=1), 16000)
            data, rate = read_reference(str(filename))
            self.assertEqual(data.shape, (1, 64000))
            self.assertEqual(rate, 16000)
            for seconds in [1, 21]:
                sf.write(filename, np.ones(seconds * 8000) * 0.1, 8000)
                with self.assertRaises(ValueError):
                    read_reference(str(filename))
            sf.write(filename, np.zeros(4 * 8000), 8000)
            with self.assertRaises(ValueError):
                read_reference(str(filename))
            filename.write_text("this is not audio", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_reference(str(filename))

    def test_large_file_rejected_before_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "large.wav"
            with path.open("wb") as stream:
                stream.truncate(20 * 1024 * 1024 + 1)
            with self.assertRaises(ValueError):
                read_reference(str(path))


@unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch not installed")
class PipelineTests(unittest.TestCase):
    def test_switching_back_reuses_prompt_across_settings_and_paths(self):
        from engine import VoiceEngine
        import torch
        prompt_calls, generate_calls = [], []

        def prompt(**kwargs):
            prompt_calls.append(kwargs)
            torch.rand(7)  # Prompt work must not change synthesis RNG on cache hits.
            return object()

        def generate(**kwargs):
            generate_calls.append((kwargs["voice_clone_prompt"], torch.rand(1).item()))
            return [np.ones(800, dtype=np.float32) * 0.1]

        engine = VoiceEngine("cpu")
        engine.model = SimpleNamespace(device="cpu", sampling_rate=8000,
                                       create_voice_clone_prompt=prompt, generate=generate)
        try:
            with tempfile.TemporaryDirectory() as folder:
                a, b, same_a = [Path(folder) / name for name in ("a.wav", "b.wav", "new-path.wav")]
                sf.write(a, np.ones(4 * 8000) * 0.1, 8000)
                sf.write(b, np.ones(4 * 8000) * 0.2, 8000)
                same_a.write_bytes(a.read_bytes())
                reports = []
                for reference, settings in [(a, Settings()), (b, Settings()),
                                             (same_a, Settings(speed=1.1, steps=16, pause=0.1))]:
                    engine.synthesize("Xin chào.", str(reference), "", settings,
                                      report=lambda value, message: reports.append(message))
                self.assertEqual(len(prompt_calls), 2, "A → B → A must only analyze A once")
                self.assertIs(generate_calls[0][0], generate_calls[2][0])
                self.assertEqual(generate_calls[0][1], generate_calls[2][1])
                self.assertTrue(any("đã lưu" in message for message in reports))
        finally:
            engine.close()

    def test_prompt_cache_invalidates_on_audio_transcript_and_model_change(self):
        from engine import VoiceEngine
        from unittest.mock import Mock
        create_prompt = Mock(side_effect=lambda **kw: object())
        model = SimpleNamespace(device="cpu", sampling_rate=8000, create_voice_clone_prompt=create_prompt,
                                generate=lambda **kw: [np.ones(800, dtype=np.float32) * 0.1])
        engine = VoiceEngine("cpu")
        engine.model = model
        try:
            with tempfile.TemporaryDirectory() as folder:
                reference = Path(folder) / "ref.wav"
                sf.write(reference, np.ones(4 * 8000) * 0.1, 8000)
                for transcript in ["", "", "Lời mẫu.", " Lời mẫu. "]:
                    engine.synthesize("Xin chào.", str(reference), transcript, Settings())
                self.assertEqual(create_prompt.call_count, 2)
                sf.write(reference, np.ones(4 * 8000) * 0.3, 8000)
                engine.synthesize("Xin chào.", str(reference), "Lời mẫu.", Settings())
                self.assertEqual(create_prompt.call_count, 3)
                engine.model = SimpleNamespace(**model.__dict__)
                engine.synthesize("Xin chào.", str(reference), "Lời mẫu.", Settings())
                self.assertEqual(create_prompt.call_count, 4)
        finally:
            engine.close()

    def test_notebook_refresh_retains_cached_voices_and_loaded_model(self):
        from engine import VoiceEngine
        from unittest.mock import Mock
        creator = Mock(return_value=object())
        old = VoiceEngine("cpu")
        old.model = SimpleNamespace(device="cpu", sampling_rate=8000, create_voice_clone_prompt=creator,
                                    generate=lambda **kw: [np.ones(800, dtype=np.float32) * 0.1])
        current = None
        try:
            with tempfile.TemporaryDirectory() as folder:
                reference = Path(folder) / "ref.wav"
                sf.write(reference, np.ones(4 * 8000) * 0.1, 8000)
                output, _ = old.synthesize("Xin chào.", str(reference), "", Settings())
                current = VoiceEngine("cpu", previous=old)
                self.assertIs(current.model, old.model)
                self.assertIs(current._lock, old._lock)
                self.assertTrue(Path(output).is_file())
                current.synthesize("Đọc nội dung khác.", str(reference), "", Settings())
                self.assertEqual(creator.call_count, 1)
        finally:
            (current or old).close()

    def test_fake_model_exports_real_wav_and_reuses_prompt(self):
        from engine import VoiceEngine

        calls = []
        marker = object()

        def prompt(**kwargs):
            calls.append(("prompt", kwargs))
            return marker

        def generate(**kwargs):
            calls.append(("generate", kwargs))
            return [np.ones(2400, dtype=np.float32) * 0.1]

        engine = VoiceEngine("cpu")
        engine.model = SimpleNamespace(device="cpu", sampling_rate=24000,
                                       create_voice_clone_prompt=prompt, generate=generate)
        try:
            with tempfile.TemporaryDirectory() as folder:
                reference = Path(folder) / "ref.wav"
                sf.write(reference, np.ones(4 * 8000) * 0.1, 8000)
                output, status = engine.synthesize("Xin chào.\n\nTạm biệt.", str(reference),
                                                   "Đây là mẫu.", Settings(pause=0.2))
                data, rate = sf.read(output)
                self.assertEqual(rate, 24000)
                self.assertEqual(len(data), 9600)
                self.assertIn("2 đoạn", status)
                self.assertEqual(len([c for c in calls if c[0] == "prompt"]), 1)
                for _, kwargs in [c for c in calls if c[0] == "generate"]:
                    self.assertEqual(kwargs["language"], "vi")
                    self.assertIs(kwargs["voice_clone_prompt"], marker)
        finally:
            engine.close()

    def test_invalid_request_never_loads_model(self):
        from engine import VoiceEngine
        engine = VoiceEngine()
        try:
            with patch.object(engine, "_load_model") as loader:
                with self.assertRaises(ValueError):
                    engine.synthesize("", "", "", Settings())
                loader.assert_not_called()
        finally:
            engine.close()


class NotebookTests(unittest.TestCase):
    def test_setup_repairs_incompatible_preinstalled_torchcodec(self):
        import importlib.metadata
        import subprocess
        notebook = json.loads((ROOT / "VietVoice_Studio_Colab.ipynb").read_text(encoding="utf-8"))
        setup = next("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
        versions = {"torch": "2.8.0+cu128", "torchaudio": "2.8.0+cu128",
                    "torchvision": "0.23.0+cu128", "torchcodec": "0.17.0+cu130"}
        with patch("importlib.util.find_spec", return_value=object()), \
                patch("importlib.metadata.version", side_effect=lambda name: versions[name]), \
                patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="Tesla T4\n")), \
                patch("subprocess.check_call") as install, patch.object(Path, "write_text"):
            exec(compile(setup, "colab-setup", "exec"), {})
        commands = [call.args[0] for call in install.call_args_list]
        codec = [command for command in commands if "torchcodec==0.7.0" in command]
        self.assertEqual(len(codec), 1, "Repair TorchCodec even when torch/torchaudio are already pinned")
        self.assertIn("https://download.pytorch.org/whl/cpu", codec[0])
        self.assertIn("--no-deps", codec[0])

    def test_embedded_sources_match_and_cells_compile(self):
        notebook = json.loads((ROOT / "VietVoice_Studio_Colab.ipynb").read_text(encoding="utf-8"))
        code_cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(code_cells), 3)
        for index, source in enumerate(code_cells):
            compile(source, f"cell-{index}", "exec")
        extract = code_cells[1]
        import ast
        tree = ast.parse(extract)
        files = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "FILES" for t in n.targets))
        for name, content in files.items():
            self.assertEqual(content, (ROOT / name).read_text(encoding="utf-8"))
        self.assertEqual(set(files), {"voice_core.py", "engine.py", "colab_ui.py", "reference_library.py", "prompt_pack.py"})
        self.assertNotIn("launch_app", "\n".join(code_cells))
        self.assertNotIn("share=True", "\n".join(code_cells))


@unittest.skipUnless(importlib.util.find_spec("ipywidgets"), "ipywidgets not installed")
class NotebookUITests(unittest.TestCase):
    def test_native_widgets_reject_missing_reference_and_recover(self):
        import ipywidgets as widgets
        from colab_ui import build_ui

        engine = SimpleNamespace(synthesize=lambda *a, **kw: self.fail("Must validate upload first"))
        panel = build_ui(engine)
        try:
            row = next(w for w in panel.children if isinstance(w, widgets.HBox)
                       and any(isinstance(c, widgets.Button) for c in w.children))
            create, download = row.children
            self.assertTrue(download.disabled)
            create.click()
            self.assertFalse(create.disabled)
            status = next(w for w in panel.children if isinstance(w, widgets.Label)
                          and "đúng một" in w.value)
            self.assertIn("giọng mẫu", status.value)
        finally:
            panel._vietvoice_resources[1].cleanup()
            panel.close()

    def test_native_upload_and_generation(self):
        import datetime
        import ipywidgets as widgets
        from colab_ui import build_ui

        calls = []
        with tempfile.TemporaryDirectory() as folder:
            result = Path(folder) / "result.wav"
            sf.write(result, np.ones(2400) * 0.1, 24000)

            def synthesize(text, reference, transcript, settings, report):
                self.assertEqual(Path(reference).name, "reference.audio")
                self.assertEqual(Path(reference).read_bytes(), b"test upload bytes")
                self.assertNotIn("..", Path(reference).name)
                settings.validate()
                calls.append(reference)
                report(1, "Done")
                return str(result), "Đã tạo"

            panel = build_ui(SimpleNamespace(synthesize=synthesize))
            try:
                upload = next(w for w in panel.children if isinstance(w, widgets.FileUpload))
                upload.value = ({"name": "../../outside.wav", "type": "audio/wav", "size": 17,
                                 "last_modified": datetime.datetime.now(datetime.timezone.utc),
                                 "content": memoryview(b"test upload bytes")},)
                row = next(w for w in panel.children if isinstance(w, widgets.HBox)
                           and any(isinstance(c, widgets.Button) for c in w.children))
                create, download = row.children
                create.click()
                self.assertEqual(len(calls), 1)
                self.assertFalse(Path(calls[0]).exists())
                self.assertFalse(create.disabled)
                self.assertFalse(download.disabled)
            finally:
                panel._vietvoice_resources[1].cleanup()
                panel.close()

    def test_preset_voice_needs_no_upload_and_is_not_deleted(self):
        import ipywidgets as widgets
        from colab_ui import build_ui

        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "nam-cong-nghe.mp3"
            result = Path(folder) / "result.wav"
            sf.write(sample, np.ones(4 * 8000) * 0.1, 8000, format="WAV")
            sf.write(result, np.ones(8000) * 0.1, 8000)
            calls = []

            def synthesize(text, reference, transcript, settings, report):
                calls.append(reference)
                return str(result), "Done"

            panel = build_ui(SimpleNamespace(synthesize=synthesize), [
                {"name": "Nam công nghệ", "path": str(sample), "transcript": "Mẫu thử"},
            ])
            try:
                upload = next(w for w in panel.children if isinstance(w, widgets.FileUpload))
                self.assertTrue(upload.disabled)
                row = next(w for w in panel.children if isinstance(w, widgets.HBox)
                           and any(isinstance(c, widgets.Button) for c in w.children))
                row.children[0].click()
                self.assertEqual(calls, [str(sample)])
                self.assertTrue(sample.is_file())
                self.assertFalse(row.children[1].disabled)
                dropdown = next(w for w in panel.children if isinstance(w, widgets.Dropdown)
                                and w.description == "Chọn giọng")
                dropdown.value = ""
                self.assertFalse(upload.disabled)
            finally:
                panel._vietvoice_resources[1].cleanup()
                panel.close()

    def test_library_group_filter_keeps_all_158_voices_available(self):
        import ipywidgets as widgets
        from colab_ui import build_ui
        from reference_library import GROUPS

        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.wav"
            sf.write(sample, np.ones(8000) * 0.1, 8000)
            library = []
            for group, count in zip(GROUPS, [8, 50, 50, 50]):
                library.extend({"name": f"{group}-{i}", "group": group,
                                "path": str(sample) + f"-{group}-{i}"} for i in range(count))
            with patch("colab_ui.Audio", return_value="preview"), patch("colab_ui.display"):
                panel = build_ui(SimpleNamespace(), library)
                try:
                    group = next(w for w in panel.children if isinstance(w, widgets.Dropdown)
                                 and w.description == "Nhóm giọng")
                    voice = next(w for w in panel.children if isinstance(w, widgets.Dropdown)
                                 and w.description == "Chọn giọng")
                    self.assertEqual(len(voice.options), 159)  # Plus own upload.
                    group.value = "vietnamese_primary_50"
                    self.assertEqual(len(voice.options), 51)
                    group.value = "preset"
                    self.assertEqual(len(voice.options), 9)
                    group.value = "all"
                    self.assertEqual(len(voice.options), 159)
                finally:
                    panel._vietvoice_resources[1].cleanup()
                    panel.close()


class ReferenceLibraryTests(unittest.TestCase):
    def make_pack(self, folder):
        import hashlib
        import zipfile
        path = Path(folder) / "pack.zip"
        data = b"audio fixture"
        entries = [{"name": "Nam công nghệ", "file": "nam-cong-nghe.mp3",
                    "sha256": hashlib.sha256(data).hexdigest()}]
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("catalog.json", json.dumps(entries))
            bundle.writestr("nam-cong-nghe.mp3", data)
        return path

    def test_unpack_checks_manifest_and_audio_hash(self):
        from reference_library import unpack_library, read_library
        with tempfile.TemporaryDirectory() as folder:
            pack = self.make_pack(folder)
            target = Path(folder) / "samples"
            entries = unpack_library(pack, target)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "Nam công nghệ")
            (target / "nam-cong-nghe.mp3").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                read_library(target)

    def test_unpack_rejects_traversal(self):
        import zipfile
        from reference_library import unpack_library
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "pack.zip"
            with zipfile.ZipFile(pack, "w") as bundle:
                bundle.writestr("../outside.mp3", b"untrusted")
            with self.assertRaises(ValueError):
                unpack_library(pack, Path(folder) / "samples")
            self.assertFalse((Path(folder) / "outside.mp3").exists())


if __name__ == "__main__":
    unittest.main()
