import os
import sys
import subprocess
import argparse
from pathlib import Path
import whisper


def extract_wav_track(source_media: Path, target_wav: Path) -> Path:
    """
    Uses FFmpeg to strip a 16kHz mono WAV audio stream from any video/audio file
    for optimal OpenAI Whisper inference.
    """
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(source_media),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(target_wav),
    ]
    subprocess.run(
        ffmpeg_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    return target_wav


def format_clock_time(seconds: float) -> str:
    """Converts raw seconds into [MM:SS] readable timestamps."""
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def run_local_asr(media_path: str, model_tier: str = "base", lang: str = None) -> dict:
    """
    Core Stage 1 POC: Loads the Whisper model into memory and runs transcription
    on the extracted audio track.
    """
    src_path = Path(media_path).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Input file not found: {src_path}")

    temp_wav = src_path.with_suffix(".temp_16k.wav")

    try:
        print(f"[1/3] Extracting 16kHz mono audio from: {src_path.name}...")
        extract_wav_track(src_path, temp_wav)

        print(f"[2/3] Loading OpenAI Whisper '{model_tier}' model...")
        asr_engine = whisper.load_model(model_tier)

        print("[3/3] Running speech-to-text inference...")
        decode_options = {"fp16": False}
        if lang:
            decode_options["language"] = lang

        result = asr_engine.transcribe(str(temp_wav), **decode_options)
        return result

    finally:
        if temp_wav.exists():
            os.remove(temp_wav)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VoxScribe Stage 1 POC: Standalone Video/Audio Transcription CLI"
    )
    parser.add_argument("input_file", nargs="?", default=None, help="Path to the lecture video or audio file")
    parser.add_argument("--model", default="base", help="Whisper tier: tiny, base, small, medium")
    parser.add_argument("--lang", default=None, help="Optional ISO language code (e.g., en, hi)")
    args = parser.parse_args()

    if not args.input_file:
        print("Checking Whisper ASR Engine...")
        test_model = whisper.load_model("tiny")
        print("SUCCESS: Whisper 'tiny' model loaded in memory!")
        print("To transcribe a file, run: python scripts/poc_transcribe.py <path_to_media_file>")
        sys.exit(0)

    try:
        output = run_local_asr(args.input_file, model_tier=args.model, lang=args.lang)
        print("\n--- DETECTED LANGUAGE:", output.get("language", "unknown").upper(), "---\n")

        for seg in output.get("segments", []):
            start_ts = format_clock_time(seg["start"])
            end_ts = format_clock_time(seg["end"])
            print(f"[{start_ts} -> {end_ts}] {seg['text'].strip()}")

    except Exception as exc:
        print(f"Error during ASR execution: {exc}", file=sys.stderr)
        sys.exit(1)