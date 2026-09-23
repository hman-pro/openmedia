"""Normalization and exact-format handling for yt-dlp-backed sources.

The normalization layer is intentionally pure. It consumes the bounded inspection object
returned by the worker's yt-dlp binding and never lets an extractor expression cross the
Telegram boundary.
"""

from __future__ import annotations

import mimetypes
import json
import shutil
import subprocess
import resource
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from openmedia.models import Availability, FormatOption, MediaKind, MediaMetadata, SizeKind
from openmedia.presentation import sort_options
from openmedia.sources import (
    DownloadInput,
    DownloadResult,
    ErrorCategory,
    GuardedTransport,
    InspectInput,
    InspectResult,
    RateController,
    SourceAdapterError,
    codec_family,
    recognize_source_url,
)


ALLOWED_PROTOCOLS = frozenset({"https"})
YTDLP_OPTIONS: Mapping[str, Any] = {
    "skip_download": True,
    "noplaylist": True,
    "extract_flat": False,
    "ignoreconfig": True,
    "load_info_filename": None,
    "extractor_args": {"youtube": {"player_client": ["default", "android"]}},
    "quiet": True,
    "no_warnings": True,
    "proxy": "",
    "cachedir": False,
    "cookiefile": None,
    "plugin_dirs": [],
    "remote_components": set(),
    "js_runtimes": {"deno": {}},
    "allowed_extractors": ["Youtube", "LinkedIn", "Instagram"],
}

_EXTRACTOR_PLATFORM = {
    "youtube": "youtube",
    "linkedinpost": "linkedin",
    "linkedin": "linkedin",
    "instagram": "instagram",
}


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _positive_number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return value


def _size(format_info: Mapping[str, Any]) -> tuple[int | None, SizeKind]:
    exact = _positive_number(format_info.get("filesize"))
    if exact is not None:
        return int(exact), SizeKind.EXACT
    estimated = _positive_number(format_info.get("filesize_approx"))
    if estimated is not None:
        return int(estimated), SizeKind.ESTIMATED
    return None, SizeKind.UNKNOWN


def _mime(media_type: str, extension: str) -> str:
    guessed = mimetypes.types_map.get(f".{extension.lower()}")
    if guessed and guessed.split("/", 1)[0] == media_type:
        return guessed
    if media_type == "audio" and extension in {"m4a", "mp4"}:
        return "audio/mp4"
    if media_type == "video" and extension == "webm":
        return "video/webm"
    if media_type == "audio" and extension == "webm":
        return "audio/webm"
    return f"{media_type}/{extension}"


def _availability(size: int | None, kind: SizeKind, maximum: int) -> tuple[Availability, str | None]:
    if size is not None and kind is SizeKind.EXACT and size > maximum:
        return Availability.EXCLUDED, f"File exceeds the {maximum}-byte delivery limit"
    return Availability.SELECTABLE, None


def _merge_extension(video: Mapping[str, Any], audio: Mapping[str, Any]) -> str | None:
    video_codec = str(video.get("vcodec", "")).lower()
    audio_codec = str(audio.get("acodec", "")).lower()
    video_ext = str(video.get("ext", "")).lower()
    audio_ext = str(audio.get("ext", "")).lower()
    if video_ext == "mp4" and audio_ext in {"m4a", "mp4"}:
        if video_codec.startswith(("avc1", "av01")) and audio_codec.startswith("mp4a"):
            return "mp4"
    if video_ext == "webm" and audio_ext in {"webm", "opus"}:
        if video_codec.startswith("vp9") and audio_codec.startswith("opus"):
            return "webm"
    return None


def _combined_size(
    video: Mapping[str, Any], audio: Mapping[str, Any]
) -> tuple[int | None, SizeKind]:
    video_size, video_kind = _size(video)
    audio_size, audio_kind = _size(audio)
    if video_size is None or audio_size is None:
        return None, SizeKind.UNKNOWN
    # Muxing changes container overhead even when both component sizes are exact.
    kind = SizeKind.ESTIMATED
    return video_size + audio_size, kind


def normalize_info(info: Mapping[str, Any], *, max_file_bytes: int) -> InspectResult:
    """Convert one yt-dlp inspection result into immutable server-bound choices."""
    if max_file_bytes <= 0:
        raise ValueError("max_file_bytes must be positive")
    if info.get("_type") in {"playlist", "multi_video"} or info.get("entries") is not None:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_COLLECTION, stage="inspection")
    if info.get("is_live") is True or info.get("live_status") in {
        "is_live",
        "is_upcoming",
        "post_live",
    }:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_COLLECTION, stage="inspection")

    extractor = str(info.get("extractor_key") or info.get("extractor") or "").lower()
    platform = next(
        (value for key, value in _EXTRACTOR_PLATFORM.items() if extractor.startswith(key)),
        None,
    )
    media_id = _text(info.get("id"))
    canonical_url = _text(info.get("webpage_url") or info.get("original_url"))
    if platform is None or media_id is None or canonical_url is None:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    duration = _positive_number(info.get("duration"))
    metadata = MediaMetadata(
        platform=platform,
        canonical_url=canonical_url,
        media_id=media_id,
        title_or_caption=_text(info.get("title") or info.get("description")),
        creator=_text(info.get("uploader") or info.get("channel") or info.get("creator")),
        duration_seconds=float(duration) if duration is not None else None,
        thumbnail_url=_text(info.get("thumbnail")),
        media_kind=MediaKind.VIDEO,
    )

    formats_value = info.get("formats")
    if not isinstance(formats_value, list):
        raise SourceAdapterError(ErrorCategory.NO_FORMATS, stage="inspection")
    candidates = [
        item
        for item in formats_value
        if isinstance(item, Mapping)
        and item.get("protocol") in ALLOWED_PROTOCOLS
        and _text(item.get("format_id"))
        and _text(item.get("url"))
    ]
    options: list[FormatOption] = []
    video_only: list[Mapping[str, Any]] = []
    audio_only: list[Mapping[str, Any]] = []
    for item in candidates:
        # yt-dlp reports an unknown codec as None and an absent stream as "none".
        video_codec = str(item["vcodec"]).lower() if item.get("vcodec") else None
        audio_codec = str(item["acodec"]).lower() if item.get("acodec") else None
        has_video = video_codec != "none"
        has_audio = audio_codec != "none"
        if not has_video and not has_audio:
            continue
        if has_video and not has_audio:
            video_only.append(item)
        if has_audio and not has_video:
            audio_only.append(item)
        media_type = "video" if has_video else "audio"
        extension = str(item.get("ext") or "").lower()
        if extension not in {"mp4", "webm", "m4a", "opus"}:
            continue
        size, size_kind = _size(item)
        availability, reason = _availability(size, size_kind, max_file_bytes)
        options.append(
            FormatOption(
                option_id=len(options),
                adapter="yt_dlp",
                source_format_id=str(item["format_id"]),
                media_type=media_type,
                extension=extension,
                mime_type=_mime(media_type, extension),
                width=int(item["width"]) if _positive_number(item.get("width")) else None,
                height=int(item["height"]) if _positive_number(item.get("height")) else None,
                bitrate=float(item.get("tbr") or item.get("abr")) if _positive_number(item.get("tbr") or item.get("abr")) else None,
                includes_audio=has_audio if has_video else None,
                size_bytes=size,
                size_kind=size_kind,
                transport_ref={
                    "url": item["url"],
                    "headers": dict(item.get("http_headers") or {}),
                    "vcodec": video_codec,
                    "acodec": audio_codec,
                },
                availability=availability,
                unavailable_reason=reason,
            )
        )

    for video in video_only:
        for audio in audio_only:
            extension = _merge_extension(video, audio)
            if extension is None:
                continue
            size, size_kind = _combined_size(video, audio)
            availability, reason = _availability(size, size_kind, max_file_bytes)
            if size is None or size > max_file_bytes:
                availability = Availability.EXCLUDED
                reason = "Combined size is unknown or exceeds the delivery limit"
            options.append(
                FormatOption(
                    option_id=len(options),
                    adapter="yt_dlp",
                    source_format_id=f"{video['format_id']}+{audio['format_id']}",
                    media_type="video",
                    extension=extension,
                    mime_type=_mime("video", extension),
                    width=int(video["width"]) if _positive_number(video.get("width")) else None,
                    height=int(video["height"]) if _positive_number(video.get("height")) else None,
                    bitrate=float(video["tbr"]) if _positive_number(video.get("tbr")) else None,
                    includes_audio=True,
                    size_bytes=size,
                    size_kind=size_kind,
                    transport_ref={
                        "video_url": video["url"],
                        "audio_url": audio["url"],
                        "video_headers": dict(video.get("http_headers") or {}),
                        "audio_headers": dict(audio.get("http_headers") or {}),
                        "vcodec": str(video.get("vcodec")),
                        "acodec": str(audio.get("acodec")),
                    },
                    availability=availability,
                    unavailable_reason=reason,
                )
            )
    if not options:
        raise SourceAdapterError(ErrorCategory.NO_FORMATS, stage="inspection")
    ordered = sort_options(options)
    rebound = tuple(replace(option, option_id=index) for index, option in enumerate(ordered))
    return InspectResult(metadata=metadata, options=rebound)


def _inside_regular_file(path: Path, root: Path) -> Path:
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
        resolved.relative_to(resolved_root)
        info = path.lstat()
    except (OSError, ValueError) as exc:
        raise SourceAdapterError(ErrorCategory.UNSAFE_DESTINATION, stage="merge") from exc
    if path.is_symlink() or not path.is_file() or info.st_size < 0:
        raise SourceAdapterError(ErrorCategory.UNSAFE_DESTINATION, stage="merge")
    return resolved


def merge_streams(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    *,
    owned_directory: Path,
    extension: str,
    video_codec: str,
    audio_codec: str,
    output_limit: int,
    workspace_limit: int,
    timeout: float = 595.0,
) -> int:
    """Merge exactly one local video and audio stream with FFmpeg stream copy."""
    if output_limit <= 0 or workspace_limit < output_limit or timeout <= 0:
        raise ValueError("merge limits and timeout are invalid")
    root = Path(owned_directory).resolve(strict=True)
    video = _inside_regular_file(Path(video_path), root)
    audio = _inside_regular_file(Path(audio_path), root)
    output = Path(output_path)
    try:
        output.parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise SourceAdapterError(ErrorCategory.UNSAFE_DESTINATION, stage="merge") from exc
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise SourceAdapterError(ErrorCategory.UNSAFE_DESTINATION, stage="merge")
    video_family = codec_family(video_codec)
    audio_family = codec_family(audio_codec)
    compatible = (
        extension == "mp4" and video_family in {"h264", "av1"} and audio_family == "aac"
    ) or (extension == "webm" and video_family == "vp9" and audio_family == "opus")
    if not compatible:
        raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="merge")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise SourceAdapterError(
            ErrorCategory.INTERNAL,
            stage="merge",
            detail="FFmpeg and ffprobe must be installed",
        )
    from openmedia.network import workspace_usage

    used = workspace_usage(root)
    if used >= workspace_limit:
        raise SourceAdapterError(ErrorCategory.STORAGE_EXHAUSTED, stage="merge")
    write_ceiling = min(output_limit, workspace_limit - used)
    def bound_output():
        resource.setrlimit(resource.RLIMIT_FSIZE, (write_ceiling, write_ceiling))
    command = [
        ffmpeg,
        "-nostdin",
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c",
        "copy",
        "-n",
        str(output),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=timeout, preexec_fn=bound_output)
        size = output.stat().st_size
        if size > output_limit:
            raise SourceAdapterError(ErrorCategory.TOO_LARGE, stage="merge")
        if workspace_usage(root) > workspace_limit:
            raise SourceAdapterError(ErrorCategory.STORAGE_EXHAUSTED, stage="merge")
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name",
                "-of",
                "json",
                str(output),
            ],
            check=True,
            text=True,
            capture_output=True,
            timeout=min(timeout, 30.0),
        )
        streams = json.loads(probe.stdout).get("streams")
        if not isinstance(streams, list) or len(streams) != 2:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="merge")
        actual = [(item.get("codec_type"), codec_family(str(item.get("codec_name")))) for item in streams]
        if actual != [("video", video_family), ("audio", audio_family)]:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="merge")
        return size
    except subprocess.TimeoutExpired as exc:
        raise SourceAdapterError(ErrorCategory.TIMEOUT, stage="merge") from exc
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        if output.exists() and output.stat().st_size >= write_ceiling:
            output.unlink()
            category = ErrorCategory.TOO_LARGE if write_ceiling == output_limit else ErrorCategory.STORAGE_EXHAUSTED
            raise SourceAdapterError(category, stage="merge") from exc
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="merge") from exc
    finally:
        # Refused/invalid outputs never survive for later delivery.
        if output.exists() and output.is_file() and output.stat().st_size > output_limit:
            output.unlink()


def _validate_native_signature(path: Path, extension: str) -> None:
    with path.open("rb") as stream:
        prefix = stream.read(16)
    valid = {
        "mp4": len(prefix) >= 8 and prefix[4:8] == b"ftyp",
        "m4a": len(prefix) >= 8 and prefix[4:8] == b"ftyp",
        "webm": prefix.startswith(b"\x1aE\xdf\xa3"),
        "opus": prefix.startswith(b"OggS"),
    }.get(extension, False)
    if not valid:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="download")


def _validate_selected_streams(path: Path, option: FormatOption) -> None:
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file",
            "-show_entries", "stream=codec_type,codec_name,width,height", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=10)
        streams = json.loads(probe.stdout)["streams"]
        video = [s for s in streams if s.get("codec_type") == "video"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        expected_video = option.media_type == "video"
        expected_audio = option.media_type == "audio" or option.includes_audio is True
        if len(video) != int(expected_video) or len(audio) != int(expected_audio) or len(streams) != len(video) + len(audio):
            raise ValueError("stream types changed")
        reference = option.transport_ref or {}
        for kind, entries, codec_key in (("video", video, "vcodec"), ("audio", audio, "acodec")):
            if entries and reference.get(codec_key) and codec_family(entries[0]["codec_name"]) != codec_family(reference[codec_key]):
                raise ValueError("source codec changed")
        # An MP4 offered with no codec information was chosen as a last-resort "phone-playable"
        # candidate (research R1), so the promise is checked on the real file instead.
        if option.media_type == "video" and option.extension == "mp4" and not reference.get("vcodec"):
            if codec_family(video[0]["codec_name"]) != "h264":
                raise ValueError("unknown-codec MP4 video is not H.264")
            if option.includes_audio and codec_family(audio[0]["codec_name"]) != "aac":
                raise ValueError("unknown-codec MP4 audio is not AAC")
        if video and any(getattr(option, field) is not None and video[0].get(field) != getattr(option, field) for field in ("width", "height")):
            raise ValueError("source dimensions changed")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download") from exc


class YtDlpAdapter:
    """yt-dlp inspection plus guard-owned exact resource downloads."""

    name = "yt_dlp"

    def __init__(self, *, max_file_bytes: int = 50_000_000) -> None:
        self.max_file_bytes = max_file_bytes

    def inspect(
        self,
        request: InspectInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> InspectResult:
        route = recognize_source_url(request.source_url)
        if route.platform not in {"youtube", "linkedin", "instagram"}:
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="inspection")
        rate_control.acquire(route.platform, "metadata", deadline=request.deadline)
        try:
            import yt_dlp

            from openmedia.sources.http import MetadataHTTP
            client = MetadataHTTP(transport, rate_control, request, route.platform)
            options = dict(YTDLP_OPTIONS)
            options["paths"] = {"home": str(request.work_directory)}
            options["outtmpl"] = {"default": "inspection-unused.%(ext)s"}
            with client.bound(), yt_dlp.YoutubeDL(options) as extractor:
                extractor.urlopen = client.ytdlp
                info = extractor.extract_info(request.source_url, download=False)
        except SourceAdapterError:
            raise
        except Exception as exc:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection") from exc
        if not isinstance(info, Mapping):
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        result = normalize_info(info, max_file_bytes=min(self.max_file_bytes, request.output_limit))
        if result.metadata.platform != route.platform or result.metadata.media_id != route.media_id:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        return result

    def download(
        self,
        request: DownloadInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> DownloadResult:
        option = request.option
        reference = option.transport_ref
        if not isinstance(reference, Mapping):
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        rate_control.acquire(request.metadata.platform, "media", deadline=request.deadline)
        destination = request.work_directory / f"selected.{option.extension}"
        if "+" in option.source_format_id:
            video = request.work_directory / "component-video"
            audio = request.work_directory / "component-audio"
            try:
                transport.download(
                    str(reference["video_url"]),
                    video,
                    output_limit=request.output_limit,
                    workspace_limit=request.workspace_limit,
                    headers=reference.get("video_headers"),
                    deadline=request.deadline,
                )
                transport.download(
                    str(reference["audio_url"]),
                    audio,
                    output_limit=request.output_limit,
                    workspace_limit=request.workspace_limit,
                    headers=reference.get("audio_headers"),
                    deadline=request.deadline,
                )
                actual = merge_streams(
                    video,
                    audio,
                    destination,
                    owned_directory=request.work_directory,
                    extension=option.extension,
                    video_codec=str(reference.get("vcodec", "")),
                    audio_codec=str(reference.get("acodec", "")),
                    output_limit=request.output_limit,
                    workspace_limit=request.workspace_limit,
                )
            finally:
                for component in (video, audio):
                    try:
                        component.unlink()
                    except FileNotFoundError:
                        pass
        else:
            try:
                actual = transport.download(
                    str(reference["url"]),
                    destination,
                    output_limit=request.output_limit,
                    workspace_limit=request.workspace_limit,
                    headers=reference.get("headers"),
                    deadline=request.deadline,
                )
            except KeyError as exc:
                raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download") from exc
        try:
            if "+" not in option.source_format_id:
                _validate_native_signature(destination, option.extension)
            _validate_selected_streams(destination, option)
        except SourceAdapterError:
            destination.unlink(missing_ok=True)
            raise
        return DownloadResult(
            path=destination,
            actual_bytes=actual,
            media_id=request.metadata.media_id,
            source_format_id=option.source_format_id,
            media_type=option.media_type.value,
            extension=option.extension,
            mime_type=option.mime_type,
        )
