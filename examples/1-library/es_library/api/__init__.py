from es_library.api import private, public
from fastapi import FastAPI

app = FastAPI()
for router in public.router, private.router:
    app.include_router(router)
