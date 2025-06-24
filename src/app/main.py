from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.app.routers import barbers, services, appointments, addons, timeslots
from src.app.auth.router import router as auth_router
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Barbershop API",
    version="1.0.0",
    default_response_class=ORJSONResponse
)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://192.168.10.188:3000/",
    "http://172.31.48.1:3000/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(barbers.router, prefix="/api/barbers", tags=["Barbers"])
app.include_router(addons.router, prefix="/api/addons", tags=["Addons"])
app.include_router(timeslots.router, prefix="/api/timeslots", tags=["Timeslots"])


# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#
#     openapi_schema = get_openapi(
#         title="Barbershop API",
#         version="1.0.0",
#         description="API for Barbershop",
#         routes=app.routes,
#     )
#
#     openapi_schema["components"]["securitySchemes"] = {
#         "BearerAuth": {
#             "type": "http",
#             "scheme": "bearer",
#             "bearerFormat": "JWT",
#         }
#     }
#     public_paths = {
#         "/": ["get"],
#         "/api/auth/login": ["post"],
#         "/api/auth/register": ["post"],
#     }
#
#     for path, path_item in openapi_schema["paths"].items():
#         for method, method_item in path_item.items():
#             if method in public_paths.get(path, []):
#                 method_item["security"] = []
#             else:
#                 method_item.setdefault("security", [{"BearerAuth": []}])
#
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema
#
#
# app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
@app.get("/")
def root():
    return {"message": "Barbershop backend is working"}
