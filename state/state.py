import reflex as rx
import asyncio
from typing import List, Dict

class State(rx.State):
    """Globalno stanje aplikacije - analogno React useState"""
    
    
    # Repository selection state
    selected_owner: str = ""
    selected_repo: str = ""
    
    # Filter states
    time_range: str = "30" # 7, 30, or 90 days
    activity_type: str = "all"  # all, commits, pull_requests, issues, releases
    
    # Data states
    repos_list: List[Dict] = []
    repo_details: Dict = {}
    activities: List[Dict] = []
    dashboard_metrics: Dict = {}
    
    # Loading states (analogno React loading states)
    is_loading_repos: bool = False
    is_loading_details: bool = False
    is_loading_activities: bool = False
    is_loading_dashboard: bool = False
    
    # Error states
    error_message: str = ""
    
    # User state
    github_username: str = ""
    is_authenticated: bool = False

    # ===========================
    # COMPUTED PROPERTIES (za dashboard metrics)
    # ===========================
    @rx.var
    def total_repos(self) -> int:
        """Get total repos count"""
        return self.dashboard_metrics.get('total_repos', 0)
    
    @rx.var
    def total_commits(self) -> int:
        """Get total commits count"""
        return self.dashboard_metrics.get('total_commits', 0)
    
    @rx.var
    def total_prs(self) -> int:
        """Get total PRs count"""
        return self.dashboard_metrics.get('total_prs', 0)
    
    @rx.var
    def total_issues(self) -> int:
        """Get total issues count"""
        return self.dashboard_metrics.get('total_issues', 0)
    
    @rx.var
    def active_contributors(self) -> int:
        """Get active contributors count"""
        return self.dashboard_metrics.get('active_contributors', 0)
    
    @rx.var
    def activity_score(self) -> int:
        """Get activity score"""
        return self.dashboard_metrics.get('activity_score', 0)  

    @rx.var
    def repo_full_name(self) -> str:
        """Get repository full name"""
        return self.repo_details.get('full_name', 'Loading...')

    @rx.var
    def repo_description(self) -> str:
        """Get repository description"""
        return self.repo_details.get('description', '')

    @rx.var
    def repo_stars(self) -> int:
        """Get repository stars"""
        return self.repo_details.get('stars', 0)

    @rx.var
    def repo_forks(self) -> int:
        """Get repository forks"""
        return self.repo_details.get('forks', 0)

    @rx.var
    def repo_watchers(self) -> int:
        """Get repository watchers"""
        return self.repo_details.get('watchers', 0)

    @rx.var
    def repo_open_issues(self) -> int:
        """Get repository open issues"""
        return self.repo_details.get('open_issues', 0)

    # ===========================
    # AUTHENTICATION
    # ===========================
    def set_username(self, username: str):
        """Update username input"""
        self.github_username = username
    
    async def login(self):
        """Login handler"""
        if not self.github_username.strip():
            return
        self.is_authenticated = True
        # Automatski učitaj dashboard podatke nakon login-a (analogno useEffect)
        await self.load_dashboard_data()
        return rx.redirect("/dashboard")
    
    def logout(self):
        """Logout handler"""
        self.is_authenticated = False
        self.github_username = ""
        return rx.redirect("/")
    
    # ===========================
    # NAVIGATION (analogno React useNavigate)
    # ===========================

    def navigate_to_repo_details(self, owner: str, repo: str):
        """Navigate to repo details"""
        return rx.redirect(f"/repos/{owner}/{repo}")

        # ... load_repo_details treba da prima parametre ...
    async def load_repo_details_from_url(self):
        """Load repository details from URL parameters"""
        # Izvuci parametre iz URL-a
        owner = self.router.page.params.get("owner", "")
        repo = self.router.page.params.get("repo", "")
    
        if owner and repo:
            await self.load_repo_details(owner, repo)

    async def load_repo_details(self, owner: str = "", repo: str = ""):
        """Load repository details - triggered on route change"""
        self.is_loading_details = True
        self.error_message = ""
    
        # Ako parametri nisu prosleđeni, pokušaj da ih čitaš iz router-a
        if not owner or not repo:
            owner = self.router.page.params.get("owner", "")
            repo = self.router.page.params.get("repo", "")
    
        self.selected_owner = owner
        self.selected_repo = repo
    
        try:
        # Simulacija GitHub API poziva - sada koristi prave parametre!
            await asyncio.sleep(1)
        
        # VAŽNO: Svaki repo treba da ima različite podatke
        # Možeš da simuliraš različite vrednosti na osnovu imena repo-a
            import random
            random.seed(hash(repo))  # Seed na osnovu imena repo-a za konzistentne rezultate
        
            self.repo_details = {
                "owner": owner,
                "name": repo,
                "full_name": f"{owner}/{repo}",
                "description": f"Production-ready repository: {repo}",
                "language": random.choice(["Python", "JavaScript", "TypeScript", "Go"]),
                "stars": random.randint(50, 500),  # Različit broj za svaki repo
                "forks": random.randint(10, 100),
                "watchers": random.randint(5, 50),
                "open_issues": random.randint(0, 20),
                "created_at": "2023-01-15",
                "updated_at": "2 hours ago",
                "size": random.randint(1000, 5000),
                "license": "MIT",
            }
        
        # Automatski učitaj aktivnosti nakon učitavanja detalja
            await self.load_repo_activities()
        
        except Exception as e:
            self.error_message = f"Error loading repo details: {str(e)}"
        finally:
            self.is_loading_details = False
    
    # OBRIŠI async def refresh_data metodu i zameni sa:
    async def refresh_current_page(self):
        """Refresh current page data"""
        # Osvježi dashboard i repos podatke
        await self.load_dashboard_data()

    # ===========================
    # HELPER METODE ZA NAVIGACIJU
    # ===========================
    # Lista za čuvanje trenutnog indeksa
    selected_repo_index: int = -1

    def set_selected_repo_index(self, index: int):
        """Set selected repo index and navigate"""
        self.selected_repo_index = index
        if 0 <= index < len(self.repos_list):
            repo = self.repos_list[index]
            return State.navigate_to_repo_details(repo["owner"], repo["name"])
    def set_selected_repo(self, repo_data: str):
        """Set selected repo from stringified data"""
        # repo_data će biti u formatu "owner|repo_name"
        parts = repo_data.split("|")
        if len(parts) == 2:
            return State.navigate_to_repo_details(parts[0], parts[1])
    # ===========================
    # STATE UPDATES (analogno setState)
    # ===========================
    @staticmethod
    def hours_from_text(time_str: str) -> float:
        """Pretvara '2 hours ago', '1 day ago' itd. u sate"""
        num = float(time_str.split()[0])

        if "hour" in time_str:
            return num
        if "day" in time_str:
            return num * 24
        if "week" in time_str:
            return num * 24 * 7

        return 9999  # fallback ako ne prepoznamo format

    
    async def set_time_range(self, value: str):
        """Update time range filter and reload data"""
        self.time_range = value
        # Re-fetch data when filter changes (analogno useEffect dependency)
        await self.load_repo_activities()
    
    async def set_activity_type(self, value: str):
        """Update activity type filter and reload data"""
        self.activity_type = value
        # Re-fetch data when filter changes (analogno useEffect dependency)
        await self.load_repo_activities()
    
    # ===========================
    # ASYNC DATA LOADING (analogno React useEffect)
    # ===========================
    
    async def load_dashboard_data(self):
        """Load dashboard metrics - analogno useEffect on mount"""
        self.is_loading_dashboard = True
        self.error_message = ""
        
        try:
            # Simulacija API poziva (u realnoj app bi bio fetch ka GitHub API)
            await asyncio.sleep(1.5)
            
            self.dashboard_metrics = {
                "total_repos": 24,
                "total_commits": 1847,
                "total_prs": 156,
                "total_issues": 89,
                "active_contributors": 12,
                "activity_score": 92,
            }
            
            # Load repos list
            await self.load_repos_list()
            
        except Exception as e:
            self.error_message = f"Error loading dashboard: {str(e)}"
        finally:
            self.is_loading_dashboard = False
    
    async def load_repos_list(self):
        """Load user's repositories - analogno useEffect"""
        self.is_loading_repos = True
        self.error_message = ""
        
        try:
            # Simulacija GitHub API poziva
            await asyncio.sleep(1)
            
            self.repos_list = [
                {
                    "owner": self.github_username,
                    "name": "ml-pipeline",
                    "description": "Machine Learning data pipeline",
                    "language": "Python",
                    "stars": 234,
                    "forks": 45,
                    "updated": "2 hours ago",
                },
                {
                    "owner": self.github_username,
                    "name": "react-dashboard",
                    "description": "Modern React admin dashboard",
                    "language": "JavaScript",
                    "stars": 189,
                    "forks": 34,
                    "updated": "1 day ago",
                },
                {
                    "owner": self.github_username,
                    "name": "api-gateway",
                    "description": "Microservices API gateway",
                    "language": "TypeScript",
                    "stars": 156,
                    "forks": 28,
                    "updated": "3 days ago",
                },
                {
                    "owner": self.github_username,
                    "name": "devops-tools",
                    "description": "DevOps automation scripts",
                    "language": "Shell",
                    "stars": 98,
                    "forks": 19,
                    "updated": "5 days ago",
                },
                {
                    "owner": self.github_username,
                    "name": "mobile-app",
                    "description": "Cross-platform mobile application",
                    "language": "Dart",
                    "stars": 267,
                    "forks": 52,
                    "updated": "1 week ago",
                },
            ]
            
        except Exception as e:
            self.error_message = f"Error loading repos: {str(e)}"
        finally:
            self.is_loading_repos = False
        
    async def load_repo_activities(self):
        """Load repository activities based on filters"""
        self.is_loading_activities = True
        self.error_message = ""
        
        try:
            # Simulacija GitHub API poziva sa filterima
            await asyncio.sleep(1.2)
            
            # Generate activities based on time_range and activity_type
            activities_pool = []
            
            if self.activity_type in ["all", "commits"]:
                activities_pool.extend([
                    {"type": "commit", "message": "Fix authentication bug", "author": "dev1", "time": "2 hours ago"},
                    {"type": "commit", "message": "Add new feature X", "author": "dev2", "time": "5 hours ago"},
                    {"type": "commit", "message": "Update documentation", "author": "dev1", "time": "1 day ago"},
                    {"type": "commit", "message": "Refactor codebase", "author": "dev3", "time": "2 days ago"},
                ])
            
            if self.activity_type in ["all", "pull_requests"]:
                activities_pool.extend([
                    {"type": "pr", "message": "Feature: Add dark mode", "author": "dev2", "time": "3 hours ago", "status": "open"},
                    {"type": "pr", "message": "Fix: Memory leak in worker", "author": "dev1", "time": "1 day ago", "status": "merged"},
                ])
            
            if self.activity_type in ["all", "issues"]:
                activities_pool.extend([
                    {"type": "issue", "message": "Bug: Login fails on Safari", "author": "user1", "time": "4 hours ago", "status": "open"},
                    {"type": "issue", "message": "Feature request: Export to PDF", "author": "user2", "time": "12 days ago", "status": "closed"},
                ])
            
            if self.activity_type in ["all", "releases"]:
                activities_pool.extend([
                    {"type": "release", "message": "v2.1.0 - Major update", "author": "dev1", "time": "4 weeks ago"},
                ])
            
            # Koliko sati unazad gledamo
            max_hours = int(self.time_range) * 24  # 7 dana -> 168h, 30 dana -> 720h itd.

            filtered = [
                a for a in activities_pool
                if self.hours_from_text(a["time"]) <= max_hours
            ]

            self.activities = filtered
 
        except Exception as e:
            self.error_message = f"Error loading activities: {str(e)}"
        finally:
            self.is_loading_activities = False
