from uvicorn_worker import UvicornWorker


class AppUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "access_log": False,
    }
