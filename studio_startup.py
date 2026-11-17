"""Load OmniVoice on the accelerator actually available in this runtime."""
from importlib.metadata import version
from types import SimpleNamespace
import sys

for package in ('numpy', 'scipy'):
    loaded = sys.modules.get(package)
    if loaded is not None and loaded.__version__ != version(package):
        raise RuntimeError('Chọn Runtime → Restart session, rồi chạy lại ô khởi động (không cần cài lại).')

import numpy as np
import scipy.linalg
import torch
import transformers as _tf

if not hasattr(torch, '_utils') and hasattr(torch._C, '_utils'):
    torch._utils = torch._C._utils

if not hasattr(_tf, 'AutoFeatureExtractor'):
    class _SafeAutoFeatureExtractor:
        @staticmethod
        def from_pretrained(model_name, **kwargs):
            from transformers import AutoConfig
            config = AutoConfig.from_pretrained(model_name, **kwargs)
            return SimpleNamespace(sampling_rate=getattr(config, 'sampling_rate', 24000))
    _tf.AutoFeatureExtractor = _SafeAutoFeatureExtractor

from omnivoice import OmniVoice, OmniVoiceGenerationConfig

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
dtype = torch.float16 if torch.cuda.is_available() else torch.float32
if device == 'cpu':
    torch.set_num_threads(min(4, torch.get_num_threads()))
    print('Đang dùng CPU: tạo giọng chậm hơn GPU. Có thể chọn T4 trong Runtime → Change runtime type.', flush=True)
else:
    print('GPU:', torch.cuda.get_device_name(0), flush=True)

if 'model' not in globals() or str(model.device) != device:
    print('Đang tải OmniVoice…', flush=True)
    model = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map=device,
                                      dtype=dtype, load_asr=False)
print('MODEL_READY', device, '—', model.sampling_rate, 'Hz', flush=True)
