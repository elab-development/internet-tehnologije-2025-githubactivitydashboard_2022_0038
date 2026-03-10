import reflex as rx
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta

API_URL = "http://backend:5000/api"


class State(rx.State):
    # ─── Auth ─────────────────────────────────────────────────────
    github_username: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""
    access_token: str = ""          # ← JEDAN token, svuda access_token
    is_authenticated: bool = False
    current_user: Dict = {}

    # ─── Filter ───────────────────────────────────────────────────
    time_range: str = "30"
    activity_type: str = "all"

    # ─── Data ─────────────────────────────────────────────────────
    repos_list: List[Dict] = []
    repo_details: Dict = {}
    activities: List[Dict] = []
    dashboard_metrics: Dict = {}

    # ─── Loading ──────────────────────────────────────────────────
    is_loading_repos: bool = False
    is_loading_details: bool = False
    is_loading_activities: bool = False
    is_loading_dashboard: bool = False

    # ─── Messages ─────────────────────────────────────────────────
    error_message: str = ""
    success_message: str = ""

    # ─── Repo selection ───────────────────────────────────────────
    selected_owner: str = ""
    selected_repo: str = ""
    selected_repo_index: int = -1

    # ===========================
    # COMPUTED PROPERTIES
    # ===========================

    @rx.var
    def total_repos(self) -> int:
        return self.dashboard_metrics.get('counts', {}).get('repositories', 0)

    @rx.var
    def total_commits(self) -> int:
        return self.dashboard_metrics.get('counts', {}).get('commits', 0)

    @rx.var
    def total_prs(self) -> int:
        return self.dashboard_metrics.get('counts', {}).get('pull_requests', 0)

    @rx.var
    def total_issues(self) -> int:
        return self.dashboard_metrics.get('counts', {}).get('issues', 0)

    @rx.var
    def active_contributors(self) -> int:
        return self.dashboard_metrics.get('active_contributors', 0)

    @rx.var
    def activity_score(self) -> int:
        return min(100, self.total_commits + self.total_prs + self.total_issues)

    @rx.var
    def repo_full_name(self) -> str:
        return self.repo_details.get('full_name', '')

    @rx.var
    def repo_description(self) -> str:
        return self.repo_details.get('description', '')

    @rx.var
    def repo_stars(self) -> int:
        return self.repo_details.get('stars', 0)

    @rx.var
    def repo_forks(self) -> int:
        return self.repo_details.get('forks', 0)

    @rx.var
    def repo_watchers(self) -> int:
        return self.repo_details.get('watchers', 0)

    @rx.var
    def repo_open_issues(self) -> int:
        return self.repo_details.get('open_issues', 0)

    @rx.var
    def user_role(self) -> str:
        return self.current_user.get('role', 'viewer')

    # ===========================
    # HELPERS
    # ===========================

    def _headers(self) -> Dict:
        """JWT header za sve zahteve"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def api_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        url = f"{API_URL}{endpoint}"
        headers = self._headers()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=data)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code == 401:
                    self.is_authenticated = False
                    self.access_token = ""
                    return {"error": "Unauthorized - please login again"}

                return response.json()

        except httpx.ConnectError:
            return {"error": "Ne mogu da se povežem sa serverom"}
        except Exception as e:
            return {"error": str(e)}

    # ===========================
    # AUTH
    # ===========================

    def set_username(self, value: str):
        self.github_username = value

    def set_email(self, value: str):
        self.email = value

    def set_password(self, value: str):
        self.password = value

    def set_confirm_password(self, value: str):
        self.confirm_password = value

    async def login(self):
        """Login i sačuvaj token u access_token"""
        if not self.github_username.strip() or not self.password.strip():
            self.error_message = "Username i lozinka su obavezni"
            return

        self.error_message = ""
        self.is_loading_dashboard = True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{API_URL}/auth/login",
                    json={
                        "username": self.github_username,
                        "password": self.password,
                    },
                )

            if r.status_code == 200:
                data = r.json()
                self.access_token = data["access_token"]   # ← uvek access_token
                self.current_user = data.get("user", {})
                self.is_authenticated = True
                self.password = ""
                self.is_loading_dashboard = False
                return rx.redirect("/dashboard")
            else:
                self.error_message = r.json().get("error", "Pogrešni kredencijali")

        except Exception as e:
            self.error_message = f"Greška: {str(e)}"

        self.is_loading_dashboard = False

    async def logout(self):
        self.access_token = ""
        self.is_authenticated = False
        self.github_username = ""
        self.current_user = {}
        self.repos_list = []
        self.dashboard_metrics = {}
        self.repo_details = {}
        self.activities = []
        self.error_message = ""
        return rx.redirect("/")

    async def register(self):
        if self.password != self.confirm_password:
            self.error_message = "Lozinke se ne poklapaju"
            return

        if not self.github_username or not self.email or not self.password:
            self.error_message = "Sva polja su obavezna"
            return

        result = await self.api_request("POST", "/auth/register", {
            "username": self.github_username,
            "email": self.email,
            "password": self.password,
        })

        if "error" in result:
            self.error_message = result["error"]
        else:
            self.success_message = "Registracija uspešna! Molimo prijavite se."
            self.email = ""
            self.password = ""
            self.confirm_password = ""

    # ===========================
    # DASHBOARD
    # ===========================

    async def load_dashboard_data(self):
        self.is_loading_dashboard = True
        self.error_message = ""

        stats = await self.api_request("GET", "/stats/overview")
        if "error" not in stats:
            self.dashboard_metrics = stats
        else:
            self.error_message = stats["error"]

        repos = await self.api_request("GET", "/repositories", {"page": 1, "per_page": 20})
        if "error" not in repos:
            self.repos_list = repos.get("repositories", [])

        self.is_loading_dashboard = False

    async def fetch_dashboard(self):
        await self.load_dashboard_data()

    # ===========================
    # REPOSITORIES
    # ===========================
    async def load_repos_list(self):
        """Load repositories from backend"""
        self.is_loading_repos = True
        self.error_message = ""
        
        try:
            result = await self.api_request("GET", "/repositories", {
                "page": 1,
                "per_page": 20
            })
            
            if "error" in result:
                self.error_message = result["error"]
            else:
                self.repos_list = result.get("repositories", [])
                
        except Exception as e:
            self.error_message = f"Error loading repositories: {str(e)}"
        finally:
            self.is_loading_repos = False
    # async def load_repos_list(self):
    #     """Dohvata repozitorijume sa GitHub API-ja za ulogovanog korisnika"""
    #     self.is_loading_repos = True
    #     self.error_message = ""

    #     if self.github_username:
    #         result = await self.api_request(
    #             "GET",
    #             f"/github/user/{self.github_username}/repos",
    #             {"sort": "updated", "per_page": 30},
    #         )
    #         if "error" not in result:
    #             self.repos_list = result.get("repos", [])
    #         else:
    #             # Fallback na lokalnu bazu
    #             result = await self.api_request(
    #                 "GET", "/repositories", {"page": 1, "per_page": 20}
    #             )
    #             if "error" not in result:
    #                 self.repos_list = result.get("repositories", [])
    #     else:
    #         result = await self.api_request(
    #             "GET", "/repositories", {"page": 1, "per_page": 20}
    #         )
    #         if "error" not in result:
    #             self.repos_list = result.get("repositories", [])

    #     self.is_loading_repos = False

    # ===========================
    # REPO DETAILS
    # ===========================

    # async def load_repo_details_from_url(self):
    #     """Dohvata detalje repozitorijuma iz URL parametara"""
    #     self.is_loading_details = True
    #     self.error_message = ""

    #     owner     = self.router.page.params.get("owner", "")
    #     repo_name = self.router.page.params.get("repo", "")

    #     if not owner or not repo_name:
    #         self.error_message = "Nedostaju parametri URL-a"
    #         self.is_loading_details = False
    #         return

    #     result = await self.api_request(
    #         "GET", f"/github/repo/{owner}/{repo_name}"
    #     )

    #     if "error" not in result:
    #         self.repo_details = result          # ← čuvaj u repo_details dict
    #         self.selected_owner = owner
    #         self.selected_repo = repo_name

    #         # Aktivnosti = poslednji commitovi
    #         self.activities = [
    #             {
    #                 "type":    "commit",
    #                 "message": c.get("message", ""),
    #                 "author":  c.get("author", ""),
    #                 "time":    c.get("date", "")[:10],
    #             }
    #             for c in result.get("recent_commits", [])
    #         ]
    #     else:
    #         self.error_message = result["error"]

    #     self.is_loading_details = False
    async def load_repo_details_by_id(self, repo_id: int):
        """Load repository details by ID"""
        self.is_loading_details = True
        self.error_message = ""
        
        result = await self.api_request("GET", f"/repositories/{repo_id}")
        
        if "error" in result:
            self.error_message = result["error"]
        else:
            self.repo_details = result
            self.selected_owner = result.get("owner", "")
            self.selected_repo = result.get("name", "")
            
            # Load activities for this repository
            await self.load_repo_activities_by_id(repo_id)
        
        self.is_loading_details = False
    async def load_repo_details_from_url(self):
        """Load repository details from URL parameters"""
        owner = self.router.page.params.get("owner", "")
        repo = self.router.page.params.get("repo", "")
        
        if owner and repo:
            # Find repository ID from repos_list or search
            repo_id = None
            for r in self.repos_list:
                if r.get("owner") == owner and r.get("name") == repo:
                    repo_id = r.get("id")
                    break
            
            if repo_id:
                await self.load_repo_details_by_id(repo_id)
            else:
                # If not in list, try to find by name
                print()
                # await self.search_and_load_repo(owner, repo)
    # ===========================
    # ACTIVITIES
    # ===========================

    # async def load_repo_activities(self):
    #     self.is_loading_activities = True
    #     self.error_message = ""

    #     params = {"page": 1, "per_page": 50}

    #     if self.activity_type != "all":
    #         type_map = {
    #             "commits":       "push",
    #             "pull_requests": "pull_request",
    #             "issues":        "issue",
    #             "releases":      "create",
    #         }
    #         params["type"] = type_map.get(self.activity_type, self.activity_type)

    #     if self.repo_details.get("id"):
    #         params["repository_id"] = self.repo_details["id"]

    #     result = await self.api_request("GET", "/activities", params)

    #     if "error" not in result:
    #         self.activities = result.get("activities", [])
    #     else:
    #         self.error_message = result["error"]

    #     self.is_loading_activities = False
    async def load_repo_activities(self):
        self.is_loading_activities = True
        self.error_message = ""

        params = {"page": 1, "per_page": 50}

        if self.activity_type != "all":
            type_map = {
                "commits":       "push",
                "pull_requests": "pull_request",
                "issues":        "issue",
                "releases":      "create",
            }
            params["type"] = type_map.get(self.activity_type, self.activity_type)

        if self.repo_details.get("id"):
            params["repository_id"] = self.repo_details["id"]

        result = await self.api_request("GET", "/activities", params)

        if "error" not in result:
        # ← Isti remapping
            self.activities = [
                {
                    "type":    a.get("activity_type", "commit"),
                    "message": a.get("ref") or a.get("action") or "No message",
                    "author":  a.get("actor", "Unknown"),
                    "time":    (a.get("timestamp") or "")[:10],
                }
                for a in result.get("activities", [])
            ]
        else:
            self.error_message = result["error"]

        self.is_loading_activities = False
    # async def load_repo_activities_by_id(self, repo_id: int):
    #     """Load activities for specific repository"""
    #     self.is_loading_activities = True
    #     self.error_message = ""
        
    #     try:
    #         result = await self.api_request("GET", f"/activities/repository/{repo_id}", {
    #             "page": 1,
    #             "per_page": 50
    #         })
            
    #         if "error" in result:
    #             self.error_message = result["error"]
    #         else:
    #             self.activities = result.get("activities", [])
                
    #     except Exception as e:
    #         self.error_message = f"Error loading repository activities: {str(e)}"
    #     finally:
    #         self.is_loading_activities = False
    async def load_repo_activities_by_id(self, repo_id: int):
        self.is_loading_activities = True
        self.error_message = ""

        try:
            result = await self.api_request("GET", f"/activities/repository/{repo_id}", {
                "page": 1,
                "per_page": 50
            })

            if "error" in result:
                self.error_message = result["error"]
            else:
            # ← Remapuj polja da odgovaraju frontendu
                self.activities = [
                    {
                        "type":    a.get("activity_type", "commit"),
                        "message": a.get("ref") or a.get("action") or "No message",
                        "author":  a.get("actor", "Unknown"),
                        "time":    (a.get("timestamp") or "")[:10],
                    }
                    for a in result.get("activities", [])
                ]

        except Exception as e:
            self.error_message = f"Error: {str(e)}"
        finally:
            self.is_loading_activities = False
    # ===========================
    # FILTERS
    # ===========================

    async def set_time_range(self, value: str):
        self.time_range = value
        await self.load_repo_activities()

    async def set_activity_type(self, value: str):
        self.activity_type = value
        await self.load_repo_activities()

    # ===========================
    # NAVIGATION
    # ===========================

    def navigate_to_repo_details(self, owner: str, repo: str):
        return rx.redirect(f"/repos/{owner}/{repo}")

    def set_selected_repo_index(self, index: int):
        self.selected_repo_index = index
        if 0 <= index < len(self.repos_list):
            repo = self.repos_list[index]
            return self.navigate_to_repo_details(
                repo.get("owner", ""), repo.get("name", "")
            )
    # ===========================
    # GITHUB SEARCH (NOVO)
    # ===========================

    github_search_query: str = ""
    github_search_result: Dict = {}
    github_search_repos: List[Dict] = []
    github_search_error: str = ""
    is_searching_github: bool = False
    sync_success_message: str = ""

    def set_github_search_query(self, value: str):
        self.github_search_query = value
        self.github_search_error = ""

    async def handle_search_key(self, key: str):
        if key == "Enter":
            await self.search_github_user()

    async def search_github_user(self):
        if not self.github_search_query.strip():
            self.github_search_error = "Unesite GitHub username"
            return

        self.is_searching_github = True
        self.github_search_result = {}
        self.github_search_repos = []
        self.github_search_error = ""

        # Dohvati profil
        result = await self.api_request(
            "GET", f"/github/user/{self.github_search_query.strip()}"
        )

        if "error" in result:
            self.github_search_error = f"Korisnik nije pronađen: {self.github_search_query}"
            self.is_searching_github = False
            return

        self.github_search_result = result

        # Dohvati repozitorijume
        repos_result = await self.api_request(
            "GET",
            f"/github/user/{self.github_search_query.strip()}/repos",
            {"sort": "updated", "per_page": 10},
        )

        if "error" not in repos_result:
            self.github_search_repos = repos_result.get("repos", [])

        self.is_searching_github = False

    async def sync_repo_to_db(self, owner: str, repo_name: str):
        """Sync GitHub repo u lokalnu bazu (Admin/Moderator)"""
        self.sync_success_message = ""
        result = await self.api_request(
            "POST", f"/github/repo/{owner}/{repo_name}/sync"
        )
        if "error" in result:
            self.github_search_error = result["error"]
        else:
            self.sync_success_message = f" {owner}/{repo_name} uspešno sinhronizovan u bazu!"

    async def check_auth_and_load(self):
        if not self.access_token:
            return rx.redirect("/")
        
    async def handle_oauth_callback(self):
        """Čita token iz URL-a nakon GitHub OAuth"""
        token = self.router.page.params.get("token", "")
        username = self.router.page.params.get("username", "")

        if token:
            self.access_token = token
            self.github_username = username
            self.is_authenticated = True
            await self.load_github_profile_data()
            return rx.redirect("/dashboard")
        else:
            return rx.redirect("/")
    
    async def load_github_profile_data(self):
        if not self.github_username:
            return
        self.is_loading_repos = True

    # ── Dohvati repos sa GitHub API-ja ───────────────────────────
        result = await self.api_request(
            "GET",
            f"/github/user/{self.github_username}/repos",
            {"sort": "updated", "per_page": 30},
        )

        if "error" not in result:
            raw_repos = result.get("repos", [])
            self.repos_list = raw_repos

        # ── Za svaki repo dohvati poslednje commitove kao aktivnosti
            all_activities = []
            for repo in raw_repos[:5]:  # samo prvih 5 zbog rate limita
                details = await self.api_request(
                    "GET",
                    f"/github/repo/{repo['owner']}/{repo['name']}",
                )
                if "error" not in details:
                    for c in details.get("recent_commits", [])[:3]:
                        all_activities.append({
                            "type":    "push",
                            "message": c.get("message", ""),
                            "author":  c.get("author", ""),
                            "time":    (c.get("date") or "")[:10],
                            "repo":    repo["full_name"],
                        })

            self.activities = all_activities

        self.is_loading_repos = False

    # ── Učitaj i dashboard stats iz lokalne baze ──────────────────
        await self.load_dashboard_data()