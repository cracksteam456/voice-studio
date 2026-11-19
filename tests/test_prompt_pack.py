import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np
import soundfile as sf

from prompt_pack import IDENTITY, MODEL_REVISION, audio_key, import_pack, read_manifest


class PackValidationTests(unittest.TestCase):
    def test_missing_release_falls_back_without_claiming_precomputed_voices(self):
        from urllib.error import HTTPError
        from prompt_pack import download_prompts
        library = [{"name": "Mẫu chưa phân tích", "sha256": "a" * 64}]
        with patch("prompt_pack.urlopen", side_effect=HTTPError("https://github.com", 404, "Missing", {}, None)):
            self.assertIs(download_prompts(library), library)
        self.assertNotIn("prompt_path", library[0])

    def test_rejects_parent_paths_before_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "pack.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.pt", b"untrusted")
            with self.assertRaises(ValueError):
                import_pack(archive, Path(folder) / "prompts", [])
            self.assertFalse((Path(folder) / "escape.pt").exists())

    def test_rejects_wrong_model_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "manifest.json").write_text(json.dumps({**IDENTITY, "revision": "wrong", "voices": []}))
            with self.assertRaisesRegex(ValueError, "phiên bản"):
                read_manifest(root)

    def test_key_changes_with_audio_rate_or_transcript(self):
        audio = np.ones((1, 16000), dtype=np.float32) * 0.2
        key = audio_key((audio, 8000))
        self.assertNotEqual(key, audio_key((audio, 16000)))
        self.assertNotEqual(key, audio_key((audio * 2, 8000)))
        self.assertNotEqual(key, audio_key((audio, 8000), "Lời khác"))
        self.assertEqual(audio_key((audio, 8000), "abc"), audio_key((audio, 8000), " abc "))


@unittest.skipUnless(importlib.util.find_spec("omnivoice"), "OmniVoice not installed")
class PersistentPromptTests(unittest.TestCase):
    def test_prepare_then_new_engine_never_analyzes_reference(self):
        import torch
        from omnivoice import VoiceClonePrompt
        from engine import VoiceEngine
        from prompt_pack import prepare_pack
        from voice_core import Settings

        prompt = VoiceClonePrompt(torch.ones((8, 100), dtype=torch.int64), "Đây là lời mẫu.", 0.1)
        make_prompt = Mock(return_value=prompt)
        common = dict(device="cpu", sampling_rate=8000,
                      config=SimpleNamespace(_name_or_path="/cache/snapshots/" + MODEL_REVISION),
                      generate=lambda **kw: [np.ones(800, dtype=np.float32) * 0.1])
        old, fresh = VoiceEngine("cpu"), VoiceEngine("cpu")
        old.model = SimpleNamespace(**common, create_voice_clone_prompt=make_prompt)
        forbid_analysis = Mock(side_effect=AssertionError("Persistent prompt must skip ASR and encoding"))
        fresh.model = SimpleNamespace(**common, create_voice_clone_prompt=forbid_analysis)
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                reference = root / "ref.wav"
                sf.write(reference, np.ones(4 * 8000) * 0.1, 8000)
                library = [{"name": "Mẫu công khai", "path": str(reference),
                            "sha256": hashlib.sha256(reference.read_bytes()).hexdigest()}]
                archive = prepare_pack(old, library, root / "prepare", report=lambda message: None)
                self.assertEqual(make_prompt.call_count, 1)
                # Re-running preparation resumes completed entries.
                prepare_pack(old, library, root / "prepare", report=lambda message: None)
                self.assertEqual(make_prompt.call_count, 1)
                self.assertEqual(import_pack(archive, root / "imported", library), 1)
                other_library = [{"name": "Audio khác", "sha256": "0" * 64}]
                self.assertEqual(import_pack(archive, root / "different", other_library), 0)
                self.assertNotIn("prompt_path", other_library[0])
                fresh.use_prepared_library(library)
                reports = []
                output, _ = fresh.synthesize("Nội dung mới.", str(reference), "", Settings(),
                                              report=lambda value, text: reports.append(text))
                self.assertTrue(Path(output).is_file())
                self.assertTrue(any("GitHub" in message for message in reports))
                forbid_analysis.assert_not_called()
                # Tampered prompt data is rejected on the next cold load.
                Path(library[0]["prompt_path"]).write_bytes(b"tampered")
                with self.assertRaises(ValueError):
                    read_manifest(root / "imported")
        finally:
            old.close()
            fresh.close()

    def test_invalid_token_dtype_is_rejected(self):
        import torch
        from omnivoice import VoiceClonePrompt
        from prompt_pack import load_prompt

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "invalid.pt"
            VoiceClonePrompt(torch.ones((8, 10), dtype=torch.float32), "abc", 0.1).save(str(target))
            with self.assertRaisesRegex(ValueError, "không hợp lệ"):
                load_prompt(target)
