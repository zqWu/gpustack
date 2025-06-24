from contextlib import asynccontextmanager
from pathlib import Path
import aiohttp
from fastapi import FastAPI
from fastapi_cdn_host import patch_docs

from gpustack import __version__
from gpustack.api import exceptions, middlewares
from gpustack.config.config import Config
from gpustack.routes import ui
from gpustack.routes.routes import api_router


def create_app(cfg: Config) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # https://fastapi.tiangolo.com/advanced/events/#lifespan-function
        # 相当于 @app.on_event("startup") / @app.on_event("shutdown") 放在一起
        app.state.http_client = aiohttp.ClientSession()  # app提供服务之前
        yield  # 开始提供服务
        await app.state.http_client.close()  # 清理工作
        # client = aiohttp.ClientSession() 相当于一个 可复用的http连接池
        # async with client.get(url) as resp:
        #   return {"status": resp.status, "content": await resp.text() }
        # 由此可以看到, 在gpustack 的FastAPI中, 会发请求到其他 http server

    app = FastAPI(
        title="GPUStack",
        lifespan=lifespan,
        response_model_exclude_unset=True,
        version=__version__,
        docs_url=None if (cfg and cfg.disable_openapi_docs) else "/docs",
        redoc_url=None if (cfg and cfg.disable_openapi_docs) else "/redoc",
        openapi_url=None if (cfg and cfg.disable_openapi_docs) else "/openapi.json",
    )

    # 与这不同 app.mount("/static", StaticFiles(directory="ui/static"))
    patch_docs(app, Path(__file__).parents[1] / "ui" / "static")
    # app.add_middleware(middlewares.RequestLogger)
    app.add_middleware(middlewares.RequestTimeMiddleware)
    app.add_middleware(middlewares.ModelUsageMiddleware)
    app.add_middleware(middlewares.RefreshTokenMiddleware)
    app.include_router(api_router)
    ui.register(app)
    exceptions.register_handlers(app)

    return app
