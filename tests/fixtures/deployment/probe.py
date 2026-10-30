"""Offline synthetic runtime probe. Never authenticate or start a polling bot."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yt_dlp_ejs
from openmedia.__main__ import RuntimeHealth, check_runtime_health
from openmedia.sources.ytdlp import merge_streams


def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=30).stdout


def main() -> None:
    assert os.getuid() == os.getgid() == 10001
    status = Path('/proc/self/status').read_text()
    assert 'CapEff:\t0000000000000000' in status
    assert 'NoNewPrivs:\t1' in status
    root_mount = next(line.split() for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1] == '/')
    assert 'ro' in root_mount[3].split(',')
    try:
        Path('/app/probe-write-forbidden').write_text('forbidden')
    except OSError:
        pass
    else:
        raise AssertionError('root filesystem writable')
    # Bind-file secret access is verified as the actual production identity.
    assert Path('/run/secrets/telegram_bot_token').read_text().startswith('123456789:')
    try:
        Path('/run/secrets/telegram_bot_token').write_text('forbidden')
    except OSError:
        pass
    else:
        raise AssertionError('secret mount writable')
    try:
        Path('/negative/unreadable').read_bytes()
    except PermissionError:
        pass
    else:
        raise AssertionError('UID 10001 can read protected negative fixture')
    assert importlib.metadata.version('yt-dlp-ejs')
    assert yt_dlp_ejs.__file__
    assert run('deno', 'eval', '--no-remote', 'console.log("bundled-deno-ok")').strip() == 'bundled-deno-ok'
    versions = {name: run(name, '-version' if name.startswith('ff') else '--version').splitlines()[0]
        for name in ('python', 'deno', 'ffmpeg', 'ffprobe')}
    with tempfile.TemporaryDirectory(dir='/tmp') as scratch:
        root = Path(scratch)
        fs = os.statvfs(root)
        assert 0 < fs.f_blocks * fs.f_frsize <= 536870912
        (root / 'scratch').write_bytes(b'scratch')
        video, audio, output = root / 'video.mp4', root / 'audio.m4a', root / 'merged.mp4'
        # Same CC0 synthetic expressions as tests/fixtures/media/README.md.
        run('ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=size=32x32:rate=5:duration=1',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', str(video))
        run('ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
            '-c:a', 'aac', '-vn', str(audio))
        merge_streams(video, audio, output, owned_directory=root, extension='mp4',
            video_codec='h264', audio_codec='aac', output_limit=1000000, workspace_limit=2000000)
        def packets(path: Path, selector: str) -> list[str]:
            value = json.loads(run('ffprobe', '-v', 'error', '-select_streams', selector,
                '-show_packets', '-show_data_hash', 'sha256', '-show_entries', 'packet=data_hash', '-of', 'json', str(path)))
            return [packet['data_hash'] for packet in value['packets']]
        assert packets(video, 'v') == packets(output, 'v')
        assert packets(audio, 'a') == packets(output, 'a')
        health = RuntimeHealth(root / 'health', wall_time=lambda: 100.)
        assert not check_runtime_health(health.path, wall_time=lambda: 100.)[0]
        health.record_successful_poll()  # Synthetic clock/state only; no Telegram request.
        assert check_runtime_health(health.path, wall_time=lambda: 101.)[0]
        assert not check_runtime_health(health.path, wall_time=lambda: 191.)[0]
        health.remove()
    print(json.dumps({'result': 'pass', 'versions': versions,
        'scope': 'offline tools, native packets, storage, permissions and synthetic health; no real polling'}))


if __name__ == '__main__':
    main()
