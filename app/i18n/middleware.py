from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.i18n import SUPPORTED_LANGS

_DEFAULT_LANG = "pt"


def _parse_accept_language(header: str) -> str | None:
    """Parse Accept-Language header, return best supported language or None."""
    parts = []
    for item in header.split(","):
        item = item.strip()
        if ";q=" in item:
            lang, q = item.split(";q=")
            try:
                parts.append((lang.strip(), float(q)))
            except ValueError:
                parts.append((lang.strip(), 0.0))
        else:
            parts.append((item, 1.0))
    parts.sort(key=lambda x: x[1], reverse=True)
    for lang, _ in parts:
        short = lang.split("-")[0].lower()
        if short in SUPPORTED_LANGS:
            return short
    return None


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        lang = None

        # 1. Query param ?lang=xx
        query_lang = request.query_params.get("lang")
        if query_lang and query_lang in SUPPORTED_LANGS:
            parsed = urlparse(str(request.url))
            params = parse_qs(parsed.query)
            params.pop("lang", None)
            clean_query = urlencode(params, doseq=True)
            clean_url = urlunparse(parsed._replace(query=clean_query))
            response = RedirectResponse(clean_url, status_code=307)
            response.set_cookie("lang", query_lang, max_age=365 * 86400, samesite="lax")
            return response

        # 2. Cookie
        cookie_lang = request.cookies.get("lang")
        if cookie_lang and cookie_lang in SUPPORTED_LANGS:
            lang = cookie_lang

        # 3. Accept-Language header
        if not lang:
            accept = request.headers.get("accept-language", "")
            if accept:
                lang = _parse_accept_language(accept)

        # 4. Fallback
        request.state.lang = lang or _DEFAULT_LANG
        response = await call_next(request)
        return response
