"""SiteDown — Neomon Proving Grounds"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import config
import logging

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(config.APP_NAME)

app = FastAPI(title=config.APP_TITLE, version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from faults import engine as fault_engine

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("noc_overview.html", {
        "request": request, "config": config,
        "active_page": "noc_overview", "effects": fault_engine.get_dashboard_effects()
    })

@app.get("/service_health")
async def service_health_page(request: Request):
    return templates.TemplateResponse("service_health.html", {
        "request": request, "config": config,
        "active_page": "service_health", "effects": fault_engine.get_dashboard_effects()
    })

@app.get("/incidents")
async def incidents_page(request: Request):
    return templates.TemplateResponse("incidents.html", {
        "request": request, "config": config,
        "active_page": "incidents", "effects": fault_engine.get_dashboard_effects()
    })

@app.get("/faults")
async def faults_page(request: Request):
    return templates.TemplateResponse("faults.html", {
        "request": request, "config": config,
        "active_page": "faults", "tiers": fault_engine.get_catalog_by_tier(),
        "active_faults": fault_engine.get_active_faults()
    })

@app.post("/api/faults/{fault_id}/activate")
async def activate_fault(fault_id: str):
    return JSONResponse(fault_engine.activate(fault_id))

@app.post("/api/faults/{fault_id}/deactivate")
async def deactivate_fault(fault_id: str):
    return JSONResponse(fault_engine.deactivate(fault_id))

@app.get("/api/faults")
async def get_faults():
    return JSONResponse({
        "catalog": fault_engine.get_catalog_by_tier(),
        "active": fault_engine.get_active_faults()
    })

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": config.APP_NAME, "active_faults": len(fault_engine.get_active_faults())}
