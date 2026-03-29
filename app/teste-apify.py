from pathlib import Path
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from yt_dlp import YoutubeDL


SOURCE_URL = "https://www.youtube.com/watch?v=9XfJSNx8tko&list=PLdG8wZb3L3C-9RouEL6e2vIXBnUeAdbZi"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "texto"
PLAYLIST_OUTPUT_PATH = OUTPUT_DIR / "teste-apify-pl.txt"
FAILURES_OUTPUT_PATH = OUTPUT_DIR / "falhas-apify.txt"
APIFY_TOKEN_ENV = "APIFY_API_TOKEN"
APIFY_ACTOR_ENV = "APIFY_YOUTUBE_SCRAPER_ACTOR_ID"
APIFY_SUBTITLES_LANGUAGE_ENV = "APIFY_YOUTUBE_SUBTITLES_LANGUAGE"
APIFY_PREFER_AUTO_GENERATED_ENV = "APIFY_YOUTUBE_PREFER_AUTO_GENERATED_SUBTITLES"
APIFY_TIMEOUT_ENV = "APIFY_YOUTUBE_TIMEOUT_SECS"
DEFAULT_APIFY_ACTOR_ID = "streamers/youtube-scraper"
DEFAULT_SUBTITLES_LANGUAGE = "pt"
DEFAULT_TIMEOUT_SECS = 180


class ApifyTranscriptError(Exception):
    pass


class ApifyConfigurationError(ApifyTranscriptError):
    pass


class ApifyTranscriptNotFoundError(ApifyTranscriptError):
    pass


class ApifyActorRunError(ApifyTranscriptError):
    pass


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


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    raise ApifyConfigurationError(f"Defina a variavel de ambiente obrigatoria {name}.")


def get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False

    raise ApifyConfigurationError(f"Valor invalido para {name}: {value}")


def get_timeout_secs() -> int:
    raw_value = os.getenv(APIFY_TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECS)).strip()
    try:
        timeout_secs = int(raw_value)
    except ValueError as exc:
        raise ApifyConfigurationError(f"Valor invalido para {APIFY_TIMEOUT_ENV}: {raw_value}") from exc

    if timeout_secs <= 0:
        raise ApifyConfigurationError(f"{APIFY_TIMEOUT_ENV} deve ser maior que zero.")

    return timeout_secs


def build_actor_run_url() -> str:
    actor_id = os.getenv(APIFY_ACTOR_ENV, DEFAULT_APIFY_ACTOR_ID).strip() or DEFAULT_APIFY_ACTOR_ID
    actor_path = actor_id.replace("/", "~")
    token = get_required_env(APIFY_TOKEN_ENV)
    return f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items?token={token}"


def build_actor_input(video_url: str) -> dict:
    subtitles_language = os.getenv(APIFY_SUBTITLES_LANGUAGE_ENV, DEFAULT_SUBTITLES_LANGUAGE).strip()
    if not subtitles_language:
        subtitles_language = DEFAULT_SUBTITLES_LANGUAGE

    return {
        "startUrls": [{"url": video_url}],
        "downloadSubtitles": True,
        "subtitlesLanguage": subtitles_language,
        "subtitlesFormat": "srt",
        "preferAutoGeneratedSubtitles": get_bool_env(APIFY_PREFER_AUTO_GENERATED_ENV, True),
    }


def run_apify_actor(video_url: str) -> list[dict]:
    payload = build_actor_input(video_url)
    request = Request(
        build_actor_run_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=get_timeout_secs()) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        details = error_body or exc.reason
        raise ApifyActorRunError(f"Apify retornou HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise ApifyActorRunError(f"Falha de rede ao chamar a Apify: {exc.reason}") from exc

    try:
        items = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ApifyActorRunError("A Apify retornou uma resposta que nao e JSON valido.") from exc

    if not isinstance(items, list):
        raise ApifyActorRunError("A Apify retornou um formato inesperado de resposta.")

    return items


def format_srt_transcript(srt_text: str) -> str:
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    parts: list[str] = []
    previous = None

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        if lines[0].isdigit():
            lines = lines[1:]

        if len(lines) < 2 or "-->" not in lines[0]:
            continue

        start_timestamp = lines[0].split("-->", 1)[0].strip().split(",", 1)[0]
        text = " ".join(lines[1:])
        text = " ".join(text.split())
        if not text or text == previous:
            continue

        parts.append(f"[{start_timestamp}] {text}")
        previous = text

    return "\n".join(parts)


def extract_transcript_text_from_item(item: dict) -> str:
    subtitles = item.get("subtitles") or []
    if not subtitles:
        raise ApifyTranscriptNotFoundError("nenhuma transcricao foi retornada pela Apify")

    for subtitle in subtitles:
        srt_text = subtitle.get("srt")
        if isinstance(srt_text, str) and srt_text.strip():
            formatted = format_srt_transcript(srt_text)
            if formatted:
                return formatted

    raise ApifyTranscriptNotFoundError("a Apify retornou legendas, mas sem conteudo SRT utilizavel")


def fetch_transcript_text(video_url: str) -> str:
    items = run_apify_actor(video_url)
    if not items:
        raise ApifyTranscriptNotFoundError("a Apify nao retornou itens para o video informado")

    return extract_transcript_text_from_item(items[0])


def get_transcript_output_path(video_id: str) -> Path:
    return OUTPUT_DIR / f"{video_id}.txt"


def save_transcript(video_id: str, video_url: str) -> Path:
    output_path = get_transcript_output_path(video_id)
    transcript_text = fetch_transcript_text(video_url)
    output_path.write_text(transcript_text + "\n", encoding="utf-8")
    return output_path


def process_video_link(link: str, attempted_keys: set[str], failed_links: list[str]) -> str:
    video_id = extract_video_id(link)
    attempt_key = video_id or f"raw:{link}"

    if attempt_key in attempted_keys:
        return "duplicate"

    attempted_keys.add(attempt_key)

    if video_id:
        print(f"Tentando baixar transcricao do video {video_id} via Apify...")
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
        output_path = save_transcript(video_id, link)
    except ApifyTranscriptNotFoundError as exc:
        add_failure_link(failed_links, link)
        print(f"Falha ao baixar a transcricao de {video_id}: {summarize_exception(exc)}.", file=sys.stderr)
        return "failed"
    except ApifyConfigurationError as exc:
        add_failure_link(failed_links, link)
        print(f"Falha de configuracao para {video_id}: {summarize_exception(exc)}.", file=sys.stderr)
        return "failed"
    except ApifyActorRunError as exc:
        add_failure_link(failed_links, link)
        print(f"Falha ao consultar a Apify para {video_id}: {summarize_exception(exc)}.", file=sys.stderr)
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
    load_dotenv()
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
