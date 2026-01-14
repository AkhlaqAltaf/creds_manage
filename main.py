from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.core.database import get_db, init_db
from src.core.auth import get_current_user_from_session
from src.routers import auth, admin , manage
from src.utils.senitization import tojson_filter
from src.views import admin_view , index_view , manage_view




app = FastAPI(
    title="Credential Manager",
    description="Secure credential management portal with role-based access control",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(manage.router)


templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates.env.filters["tojson"] = tojson_filter



@app.on_event("startup")
async def startup():
    init_db()


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Login page"""
    user = await get_current_user_from_session(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})




@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    return await admin_view.admin_access_view(request, db,templates)



@app.get("/", response_class=HTMLResponse)
async def index(request: Request, 
                page: int = Query(1, ge=1),
                per_page: int = Query(20, ge=1, le=100),
                status_filter: str = Query("all", pattern="^(all|online|offline)$"),
                checked_filter: str = Query("not_checked", pattern="^(all|checked|not_checked|checked_and_working)$"),
                accessed_only: bool = Query(False),
                domain_filter: str = Query("all", pattern="^(all|\\.in|\\.gov|\\.gov\\.in)$"),
                search: str = Query("", max_length=100),
                db: Session = Depends(get_db)):

    return await index_view.index_view(request, page, per_page, status_filter, checked_filter, accessed_only, domain_filter, search, db,templates)




@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request, db: Session = Depends(get_db)):
    return await manage_view.manage_view(request, db, templates)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)