from pathlib import Path
import random
import time
from urllib.parse import parse_qs, urlparse
import sys

from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)


SOURCE_URL = "https://www.youtube.com/watch?v=9XfJSNx8tko&list=PLdG8wZb3L3C-9RouEL6e2vIXBnUeAdbZi"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "texto"
PLAYLIST_OUTPUT_PATH = OUTPUT_DIR / "teste-pl.txt"
FAILURES_OUTPUT_PATH = OUTPUT_DIR / "falhas.txt"
YOUTUBE_REQUEST_DELAY_RANGE_SECONDS = (2, 10)


def get_source_url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return SOURCE_URL


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)

    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        return parsed.path.lstrip("/")

    return parse_qs(parsed.query).get("v", [""])[0]


def is_playlist_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parse_qs(parsed.query).get("list"))


def wait_after_youtube_transcript_api_request() -> None:
    delay_seconds = random.uniform(*YOUTUBE_REQUEST_DELAY_RANGE_SECONDS)
    print(f"Aguardando {delay_seconds:.2f}s apos requisicao ao YouTube...")
    time.sleep(delay_seconds)


def fetch_playlist_video_links(url: str) -> list[str]:
    options = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "skip_download": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info or info.get("_type") != "playlist":
        return []

    links: list[str] = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        video_url = entry.get("url")
        video_id = entry.get("id")
        if video_url:
            links.append(video_url)
        elif video_id:
            links.append(f"https://www.youtube.com/watch?v={video_id}")

    return links


def format_transcript_text(snippets) -> str:
    parts: list[str] = []
    previous = None

    for snippet in snippets:
        text = " ".join(snippet.text.split())
        if not text or text == previous:
            continue
        start_seconds = int(snippet.start)
        hours, remainder = divmod(start_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02}"
        parts.append(f"[{timestamp}] {text}")
        previous = text

    return "\n".join(parts)


def fetch_transcript_text(video_id: str) -> str:
    transcript_list = YouTubeTranscriptApi().list(video_id)
    wait_after_youtube_transcript_api_request()

    try:
        transcript = transcript_list.find_manually_created_transcript(["pt-BR", "pt", "en"])
    except NoTranscriptFound:
        transcript = transcript_list.find_generated_transcript(["pt-BR", "pt", "en"])

    snippets = transcript.fetch()
    wait_after_youtube_transcript_api_request()
    return format_transcript_text(snippets)


def get_transcript_output_path(video_id: str) -> Path:
    return OUTPUT_DIR / f"{video_id}.txt"


def summarize_exception(exc: Exception) -> str:
    for line in str(exc).splitlines():
        line = line.strip()
        if line:
            return line
    return exc.__class__.__name__


def load_failure_links() -> list[str]:
    if not FAILURES_OUTPUT_PATH.exists():
        return []

    return [
        line.strip()
        for line in FAILURES_OUTPUT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def add_failure_link(failed_links: list[str], link: str) -> None:
    if link not in failed_links:
        failed_links.append(link)


def remove_failure_link(failed_links: list[str], link: str) -> None:
    while link in failed_links:
        failed_links.remove(link)


def write_failure_links(failed_links: list[str]) -> None:
    unique_links: list[str] = []
    seen: set[str] = set()

    for link in failed_links:
        if link in seen:
            continue
        seen.add(link)
        unique_links.append(link)

    FAILURES_OUTPUT_PATH.write_text(
        "\n".join(unique_links) + ("\n" if unique_links else ""),
        encoding="utf-8",
    )
    print(f"Falhas salvas em {FAILURES_OUTPUT_PATH}")


def save_transcript(video_id: str) -> Path:
    output_path = get_transcript_output_path(video_id)
    transcript_text = fetch_transcript_text(video_id)
    output_path.write_text(transcript_text + "\n", encoding="utf-8")
    return output_path


def process_video_link(link: str, attempted_keys: set[str], failed_links: list[str]) -> str:
    video_id = extract_video_id(link)
    attempt_key = video_id or f"raw:{link}"

    if attempt_key in attempted_keys:
        return "duplicate"

    attempted_keys.add(attempt_key)

    if video_id:
        print(f"Tentando baixar transcricao do video {video_id}...")
    else:
        print(f"Tentando processar link sem video_id identificado: {link}")

    if not video_id:
        add_failure_link(failed_links, link)
        print(f"Nao foi possivel identificar o video no link: {link}", file=sys.stderr)
        return "failed"

    output_path = get_transcript_output_path(video_id)
    if output_path.exists():
        remove_failure_link(failed_links, link)
        print(f"Transcricao ja existe em {output_path}")
        return "skipped"

    try:
        output_path = save_transcript(video_id)
    except TranscriptsDisabled:
        add_failure_link(failed_links, link)
        print(f"Falha ao baixar a transcricao de {video_id}: transcricoes desabilitadas.", file=sys.stderr)
        return "failed"
    except NoTranscriptFound:
        add_failure_link(failed_links, link)
        print(f"Falha ao baixar a transcricao de {video_id}: nenhuma transcricao em portugues ou ingles.", file=sys.stderr)
        return "failed"
    except VideoUnavailable:
        add_failure_link(failed_links, link)
        print(f"Falha ao baixar a transcricao de {video_id}: video indisponivel.", file=sys.stderr)
        return "failed"
    except Exception as exc:
        add_failure_link(failed_links, link)
        print(f"Falha ao baixar a transcricao de {video_id}: {summarize_exception(exc)}", file=sys.stderr)
        return "failed"

    remove_failure_link(failed_links, link)
    print(f"Transcricao salva em {output_path}")
    return "saved"


def process_links(links: list[str], attempted_keys: set[str], failed_links: list[str]) -> tuple[int, int, int]:
    saved_count = 0
    skipped_count = 0
    failed_count = 0

    for link in links:
        status = process_video_link(link, attempted_keys, failed_links)

        if status == "saved":
            saved_count += 1
        elif status == "skipped":
            skipped_count += 1
        elif status == "failed":
            failed_count += 1
        elif status == "duplicate":
            continue

    return saved_count, skipped_count, failed_count


def process_playlist(source_url: str, attempted_keys: set[str], failed_links: list[str]) -> tuple[int, int, int, bool]:
    try:
        playlist_links = fetch_playlist_video_links(source_url)
    except Exception as exc:
        add_failure_link(failed_links, source_url)
        print(f"Falha ao listar os videos da playlist: {summarize_exception(exc)}", file=sys.stderr)
        return 0, 0, 1, False

    if not playlist_links:
        add_failure_link(failed_links, source_url)
        print("A URL possui parametro de playlist, mas nenhum video foi encontrado.", file=sys.stderr)
        return 0, 0, 1, False

    remove_failure_link(failed_links, source_url)
    PLAYLIST_OUTPUT_PATH.write_text("\n".join(playlist_links) + "\n", encoding="utf-8")
    print(f"Playlist detectada. Links salvos em {PLAYLIST_OUTPUT_PATH}")

    saved_count, skipped_count, failed_count = process_links(playlist_links, attempted_keys, failed_links)
    return saved_count, skipped_count, failed_count, True


def main() -> int:
    source_url = get_source_url()
    video_id = extract_video_id(source_url)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    attempted_keys: set[str] = set()
    failed_links = load_failure_links()
    total_saved = 0
    total_skipped = 0

    retry_links = failed_links.copy()
    if retry_links:
        print(f"Tentando novamente {len(retry_links)} links de {FAILURES_OUTPUT_PATH}")
        retry_saved, retry_skipped, retry_failed = process_links(retry_links, attempted_keys, failed_links)
        total_saved += retry_saved
        total_skipped += retry_skipped
        print(
            f"Resumo das falhas anteriores: {retry_saved} transcricoes salvas, "
            f"{retry_skipped} ja existentes, {retry_failed} falhas."
        )

    if is_playlist_url(source_url):
        saved_count, skipped_count, failed_count, playlist_found = process_playlist(
            source_url,
            attempted_keys,
            failed_links,
        )
        total_saved += saved_count
        total_skipped += skipped_count
        write_failure_links(failed_links)
        if playlist_found:
            print(
                f"Resumo da playlist: {saved_count} transcricoes salvas, "
                f"{skipped_count} ja existentes, {failed_count} falhas."
            )
        return 0 if (total_saved + total_skipped) > 0 else 1

    if not video_id:
        add_failure_link(failed_links, source_url)
        write_failure_links(failed_links)
        print("Nao foi possivel identificar o video na URL informada.", file=sys.stderr)
        return 1

    status = process_video_link(source_url, attempted_keys, failed_links)
    write_failure_links(failed_links)
    return 0 if status in {"saved", "skipped", "duplicate"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
