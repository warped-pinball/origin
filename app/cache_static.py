from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
import os
import mimetypes

class CacheStaticFiles(StaticFiles):
    """StaticFiles subclass that sets Cache-Control headers."""

    def __init__(self, directory: str, cachecontrol: str = "public, max-age=31536000", **kwargs):
        super().__init__(directory=directory, **kwargs)
        self.cachecontrol = cachecontrol

    async def get_response(self, path, scope):  # pragma: no cover - called by Starlette
        headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        if "gzip" in headers.get("accept-encoding", ""):
            gz_path = os.path.join(self.directory, path + ".gz")
            if os.path.exists(gz_path):
                media_type, _ = mimetypes.guess_type(path)
                response = FileResponse(gz_path, media_type=media_type)
                response.headers["Content-Encoding"] = "gzip"
                response.headers.setdefault("Cache-Control", self.cachecontrol)
                return response
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers.setdefault("Cache-Control", self.cachecontrol)
        return response