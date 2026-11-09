from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import accounts
from flight_repository import FlightRepository
from route_analysis import DAY_NAMES, FlightGraph, analyze_route, rank_airlines, worst_routes

app = FastAPI()
templates = Jinja2Templates(directory="templates")
repo = FlightRepository()
graph = FlightGraph(repo)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if accounts.check_credentials(username, password):
        token = accounts.create_session(username)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("session_id", token)
        return response
    return templates.TemplateResponse(request, "login.html", {"message": "Неверное имя или пароль"})


@app.get("/logout")
def logout(request: Request):
    accounts.delete_session(request)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_id")
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = accounts.get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    data = {
        "user": user,                       # имя пользователя
        "overview": repo.overview(),        # общая статистика (сколько всего рейсов и т.д.)
        "airlines": repo.airline_stats(),   # статистика по авиакомпаниям (задержки, рейтинг)
        "weather": repo.delay_by_weather(), # сколько задержек было из-за погоды
        "reasons": repo.delay_by_reason(),  # причины задержек (технические, экипаж и т.д.)
        "worst": worst_routes(repo),        # список самых проблемных маршрутов
    }
    return templates.TemplateResponse(request, "dashboard.html", data)


@app.get("/route", response_class=HTMLResponse)
def route_page(request: Request):
    user = accounts.get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    data = {"user": user, "airports": repo.airports(), "days": DAY_NAMES}
    return templates.TemplateResponse(request, "route.html", data)


@app.post("/route", response_class=HTMLResponse)
def route_submit(request: Request, origin: str = Form(...), destination: str = Form(...)):
    user = accounts.get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    stats = analyze_route(repo, origin, destination)
    data = {
        "user": user,
        "airports": repo.airports(),
        "days": DAY_NAMES,
        "origin": origin,
        "destination": destination,
        "stats": stats,
        "ranking": rank_airlines(repo, origin, destination),
    }
    if stats is None:
        data["message"] = "Для этого маршрута нет данных"
    return templates.TemplateResponse(request, "route.html", data)


@app.post("/path", response_class=HTMLResponse)
def path_submit(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    day: int = Form(...),
    time: str = Form(...),
):
    user = accounts.get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    hours, minutes = time.split(":")
    start_time = day * 1440 + int(hours) * 60 + int(minutes)

    path = graph.find_path(origin, destination, start_time)
    data = {
        "user": user,
        "airports": repo.airports(),
        "days": DAY_NAMES,
        "origin": origin,
        "destination": destination,
        "path": path,
    }
    if path is None:
        data["message"] = "Путь не найден"
    return templates.TemplateResponse(request, "route.html", data)