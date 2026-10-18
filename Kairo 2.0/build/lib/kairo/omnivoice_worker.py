import json
import sys


def main():
    request = json.loads(sys.stdin.buffer.read(32000))
    if not isinstance(request.get("text"), str) or len(request["text"]) > 5000:
        raise ValueError("Invalid speech request")
    if request.get("device") not in {"cpu", "cuda:0", "mps", "xpu"}:
        raise ValueError("Unsupported voice device")
    from omnivoice import OmniVoice
    import sounddevice
    import torch
    model = OmniVoice.from_pretrained(request["model"], device_map=request["device"], dtype=torch.float32 if request["device"] == "cpu" else torch.float16)
    audio = model.generate(text=request["text"])
    sounddevice.play(audio[0], 24000)
    sounddevice.wait()


if __name__ == "__main__":
    main()
