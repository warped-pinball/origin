from starlette.staticfiles import StaticFiles

class CacheStaticFiles(StaticFiles):
    """StaticFiles subclass that sets Cache-Control headers."""

    def __init__(self, directory: str, cachecontrol: str = "public, max-age=31536000", **kwargs):
        super().__init__(directory=directory, **kwargs)
        self.cachecontrol = cachecontrol

    async def get_response(self, path, scope):  # pragma: no cover - called by Starlette
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers.setdefault("Cache-Control", self.cachecontrol)
        return response
