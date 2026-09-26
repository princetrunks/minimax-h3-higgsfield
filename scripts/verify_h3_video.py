#!/usr/bin/env python3
"""Check that a saved MiniMax H3 MP4 has valid video and audible, varying audio."""

import argparse
import array
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Path to the generated H3 MP4")
    parser.add_argument("--width", type=int, help="Expected output width")
    parser.add_argument("--height", type=int, help="Expected output height")
    parser.add_argument("--duration", type=float, help="Expected duration in seconds")
    args = parser.parse_args()

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        return fail("ffmpeg and ffprobe must be installed and available on PATH")
    if not args.video.is_file():
        return fail(f"file not found: {args.video}")

    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,duration",
            "-of",
            "json",
            str(args.video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return fail(f"ffprobe could not read the MP4: {result.stderr.strip()}")
    try:
        metadata = json.loads(result.stdout)
        streams = metadata["streams"]
        duration = float(metadata["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return fail(f"incomplete MP4 stream metadata: {exc}")

    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not video_streams:
        return fail("the MP4 has no video stream")
    if not audio_streams:
        return fail("the MP4 has no audio stream")

    video = video_streams[0]
    width, height = int(video["width"]), int(video["height"])
    if args.width is not None and width != args.width:
        return fail(f"video is {width}x{height}; expected width {args.width}")
    if args.height is not None and height != args.height:
        return fail(f"video is {width}x{height}; expected height {args.height}")
    if args.duration is not None and abs(duration - args.duration) > 0.5:
        return fail(f"video duration is {duration:.2f}s; expected about {args.duration:.2f}s")

    thumbnail = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(args.video),
            "-map",
            "0:v:0",
            "-an",
            "-vf",
            "fps=1,scale=32:18:flags=area,format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    )
    frame_bytes = 32 * 18
    if thumbnail.returncode or not thumbnail.stdout or len(thumbnail.stdout) % frame_bytes:
        return fail("video frames could not be decoded for a black-frame check")
    frame_luma = [
        sum(thumbnail.stdout[offset : offset + frame_bytes]) / frame_bytes
        for offset in range(0, len(thumbnail.stdout), frame_bytes)
    ]
    if max(frame_luma) <= 1.0:
        return fail("all sampled video frames are black or nearly black")

    decoded = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(args.video),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "2",
            "-ar",
            "32000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    )
    if decoded.returncode:
        return fail(f"audio could not be decoded: {decoded.stderr.decode(errors='replace').strip()}")
    if not decoded.stdout or len(decoded.stdout) % 4:
        return fail("decoded audio is empty or malformed")

    samples = array.array("f")
    samples.frombytes(decoded.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return fail("decoded audio contains no samples")

    finite = [sample for sample in samples if math.isfinite(sample)]
    if len(finite) != len(samples):
        return fail("decoded audio contains NaN or infinite samples")
    minimum, maximum = min(finite), max(finite)
    mean = sum(finite) / len(finite)
    rms = math.sqrt(sum(sample * sample for sample in finite) / len(finite))
    variation = math.sqrt(sum((sample - mean) ** 2 for sample in finite) / len(finite))
    if rms < 1e-5 or variation < 1e-5:
        return fail(
            "audio is silent or constant; "
            f"RMS={rms:.3g}, variation={variation:.3g}"
        )

    print(
        "PASS: "
        f"{args.video} | {width}x{height} | {duration:.2f}s | "
        f"sampled luma max={max(frame_luma):.1f} | "
        f"audio RMS={rms:.4f}, variation={variation:.4f}, "
        f"range=[{minimum:.4f}, {maximum:.4f}]"
    )
    print("Listen to the clip once as well; this check verifies the audio stream is not silent or constant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
