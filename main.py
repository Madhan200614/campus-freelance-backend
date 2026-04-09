from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from database import engine
import models
from auth import router as auth_router
from jobs import router as jobs_router
from applications import router as applications_router
from chat import router as chat_router
from payments import router as payments_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Campus Freelance API")

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(chat_router)
app.include_router(payments_router)

@app.get("/")
def root():
    return {"message": "Campus Freelance API is running ✅"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="Campus Freelance API",
        version="1.0.0",
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi