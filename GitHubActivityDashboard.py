import reflex as rx
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta
import random
from GitHubActivityDashboard.pages.login import login_page
from GitHubActivityDashboard.pages.dashboard import dashboard_page
from GitHubActivityDashboard.pages.reposlist import repos_list_page
from GitHubActivityDashboard.pages.repodetails import repo_details_page
from GitHubActivityDashboard.state.state import State


# ===========================
# APP INITIALIZATION
# ===========================

app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)

app.add_page(
    login_page,
    route="/",
    title="GitHub Dashboard - Login"
)

app.add_page(
    dashboard_page,
    route="/dashboard",
    title="GitHub Dashboard - Dashboard",
    on_load=State.load_dashboard_data
)

app.add_page(
    repos_list_page,
    route="/repos",
    title="GitHub Dashboard - Repositories",
    on_load=State.load_repos_list
)

app.add_page(
    repo_details_page,
    route="/repos/[owner]/[repo]",
    title="GitHub Dashboard - Repository Details",
    on_load=State.load_repo_details_from_url
)