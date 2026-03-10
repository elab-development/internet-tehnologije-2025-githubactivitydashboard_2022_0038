import reflex as rx
import asyncio
from typing import List, Dict, Optional
import httpx
from datetime import datetime, timedelta

class State(rx.State):
    """Globalno stanje aplikacije sa backend integracijom"""
    
    # API client instance
    api_base_url: str = "http://localhost:5000/api"
    access_token: str = ""
    
    # Repository selection state
    selected_owner: str = ""
    selected_repo: str = ""
    
    # Filter states
    time_range: str = "30"  # 7, 30, or 90 days
    activity_type: str = "all"  # all, commits, pull_requests, issues, releases
    
    # Data states
    repos_list: List[Dict] = []
    repo_details: Dict = {}
    activities: List[Dict] = []
    dashboard_metrics: Dict = {}
    
    # Loading states
    is_loading_repos: bool = False
    is_loading_details: bool = False
    is_loading_activities: bool = False
    is_loading_dashboard: bool = False
    
    # Error states
    error_message: str = ""
    success_message: str = ""
    
    # User state
    github_username: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""
    is_authenticated: bool = False
    current_user: Dict = {}

    # ===========================
    # COMPUTED PROPERTIES
    # ===========================
    @rx.var
    def total_repos(self) -> int:
        # Backend šalje: {"counts": {"repositories": X}}
        return self.dashboard_metrics.get('counts', {}).get('repositories', 0)
    
    @rx.var
    def total_commits(self) -> int:
        # Backend šalje: {"counts": {"commits": X}}
        return self.dashboard_metrics.get('counts', {}).get('commits', 0)
    
    @rx.var
    def total_prs(self) -> int:
        # Backend šalje: {"counts": {"pull_requests": X}}
        return self.dashboard_metrics.get('counts', {}).get('pull_requests', 0)
    
    @rx.var
    def total_issues(self) -> int:
        # Backend šalje: {"counts": {"issues": X}}
        return self.dashboard_metrics.get('counts', {}).get('issues', 0)

    
    @rx.var
    def active_contributors(self) -> int:
        """Get active contributors count"""
        return self.dashboard_metrics.get('active_contributors', 12)  # Fallback
    
    @rx.var
    def activity_score(self) -> int:
        """Get activity score"""
        recent_activities = self.dashboard_metrics.get('counts', {}).get('recent_activities', 0)
        total_activities = self.dashboard_metrics.get('counts', {}).get('activities', 1)
        # Simple calculation - adjust based on your needs
        return min(100, int((recent_activities / max(total_activities, 1)) * 100))  

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

    @rx.var
    def user_role(self) -> str:
        """Get user role from backend"""
        return self.current_user.get('role', 'viewer')

    # ===========================
    # HELPER METHODS
    # ===========================
    
    async def api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make API request to backend"""
        url = f"{self.api_base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
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
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def clear_messages(self):
        """Clear error and success messages"""
        self.error_message = ""
        self.success_message = ""

    # ===========================
    # AUTHENTICATION
    # ===========================
    
    def set_username(self, username: str):
        """Update username input"""
        self.github_username = username
    
    def set_email(self, email: str):
        """Update email input"""
        self.email = email
    
    def set_password(self, password: str):
        """Update password input"""
        self.password = password
    
    def set_confirm_password(self, password: str):
        """Update confirm password input"""
        self.confirm_password = password
    
    async def register(self):
        """Register new user with backend"""
        if self.password != self.confirm_password:
            self.error_message = "Passwords do not match"
            return
        
        if not self.github_username or not self.email or not self.password:
            self.error_message = "All fields are required"
            return
        
        result = await self.api_request("POST", "/auth/register", {
            "username": self.github_username,
            "email": self.email,
            "password": self.password
        })
        
        if "error" in result:
            self.error_message = result["error"]
        else:
            self.success_message = "Registration successful! Please login."
            # Clear form
            self.email = ""
            self.password = ""
            self.confirm_password = ""
    
    async def login(self):
        """Login handler with backend"""
        if not self.github_username.strip() or not self.password.strip():
            self.error_message = "Username and password are required"
            return
        
        self.is_loading_dashboard = True
        result = await self.api_request("POST", "/auth/login", {
            "username": self.github_username,
            "password": self.password
        })
        
        if "error" in result:
            self.error_message = result["error"]
            self.is_loading_dashboard = False
        elif "access_token" in result:
            self.access_token = result["access_token"]
            self.current_user = result.get("user", {})
            self.is_authenticated = True
            self.success_message = "Login successful!"
            
            # Clear password
            self.password = ""
            
            # Automatically load dashboard data
            await self.load_dashboard_data()
            self.is_loading_dashboard = False
            
            return rx.redirect("/dashboard")
    
    async def logout(self):
        """Logout handler"""
        self.is_authenticated = False
        self.github_username = ""
        self.access_token = ""
        self.current_user = {}
        self.repos_list = []
        self.dashboard_metrics = {}
        self.error_message = ""
        self.success_message = ""
        return rx.redirect("/")
    
    async def get_current_user_info(self):
        """Get current user info from backend"""
        if not self.access_token:
            return
        
        result = await self.api_request("GET", "/auth/me")
        if "error" not in result:
            self.current_user = result

    # ===========================
    # NAVIGATION
    # ===========================

    def navigate_to_repo_details(self, owner: str, repo: str):
        """Navigate to repo details"""
        return rx.redirect(f"/repos/{owner}/{repo}")

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
                await self.search_and_load_repo(owner, repo)

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
    
    async def search_and_load_repo(self, owner: str, repo_name: str):
        """Search for repository and load details"""
        self.is_loading_details = True
        self.error_message = ""
        
        # Search for repository
        result = await self.api_request("GET", "/repositories", {
            "search": f"{owner}/{repo_name}",
            "per_page": 1
        })
        
        if "error" in result:
            self.error_message = result["error"]
        elif result.get("repositories"):
            repo = result["repositories"][0]
            self.repo_details = repo
            self.selected_owner = owner
            self.selected_repo = repo_name
            
            # Load activities
            await self.load_repo_activities_by_id(repo.get("id"))
        else:
            self.error_message = f"Repository {owner}/{repo_name} not found"
        
        self.is_loading_details = False

    # ===========================
    # HELPER METHODS FOR NAVIGATION
    # ===========================
    
    selected_repo_index: int = -1

    def set_selected_repo_index(self, index: int):
        """Set selected repo index and navigate"""
        self.selected_repo_index = index
        if 0 <= index < len(self.repos_list):
            repo = self.repos_list[index]
            return self.navigate_to_repo_details(repo.get("owner", ""), repo.get("name", ""))
    
    def set_selected_repo(self, repo_data: str):
        """Set selected repo from stringified data"""
        parts = repo_data.split("|")
        if len(parts) == 2:
            return self.navigate_to_repo_details(parts[0], parts[1])

    # ===========================
    # STATE UPDATES
    # ===========================
    
    @staticmethod
    def hours_from_text(time_str: str) -> float:
        """Convert time string to hours"""
        try:
            num = float(time_str.split()[0])
            if "hour" in time_str:
                return num
            if "day" in time_str:
                return num * 24
            if "week" in time_str:
                return num * 24 * 7
        except:
            pass
        return 9999  # fallback
    
    async def set_time_range(self, value: str):
        """Update time range filter and reload data"""
        self.time_range = value
        await self.load_repo_activities()
    
    async def set_activity_type(self, value: str):
        """Update activity type filter and reload data"""
        self.activity_type = value
        await self.load_repo_activities()
    
    async def refresh_current_page(self):
        """Refresh current page data"""
        await self.load_dashboard_data()

    # ===========================
    # ASYNC DATA LOADING
    # ===========================
    
    async def load_dashboard_data(self):
        """Load dashboard metrics from backend"""
        self.is_loading_dashboard = True
        self.error_message = ""
        
        try:
            # Get system statistics from backend
            stats_result = await self.api_request("GET", "/stats/overview")
            
            if "error" in stats_result:
                self.error_message = stats_result["error"]
            else:
                self.dashboard_metrics = stats_result
            
            # Load repositories list
            await self.load_repos_list()
            
        except Exception as e:
            self.error_message = f"Error loading dashboard: {str(e)}"
        finally:
            self.is_loading_dashboard = False
    
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
    
    async def load_repo_activities(self):
        """Load repository activities from backend with filters"""
        self.is_loading_activities = True
        self.error_message = ""
        
        try:
            # Calculate date based on time_range
            days = int(self.time_range)
            #start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Prepare filter parameters
            params = {
                "page": 1,
                "per_page": 50,
                #"start_date": start_date
            }
            
            if self.activity_type != "all":
                # Map frontend types to backend types
                type_map = {
                    "commits": "push",
                    "pull_requests": "pull_request",
                    "issues": "issue",
                    "releases": "create"
                }
                params["type"] = type_map.get(self.activity_type, self.activity_type)
            
            # If we have a selected repository, filter by it
            if self.selected_repo and self.repo_details.get("id"):
                params["repository_id"] = self.repo_details["id"]
            
            result = await self.api_request("GET", "/activities", params)
            
            if "error" in result:
                self.error_message = result["error"]
            else:
                self.activities = result.get("activities", [])
                
        except Exception as e:
            self.error_message = f"Error loading activities: {str(e)}"
        finally:
            self.is_loading_activities = False
    
    async def load_repo_activities_by_id(self, repo_id: int):
        """Load activities for specific repository"""
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
                self.activities = result.get("activities", [])
                
        except Exception as e:
            self.error_message = f"Error loading repository activities: {str(e)}"
        finally:
            self.is_loading_activities = False
    
    # ===========================
    # ADDITIONAL BACKEND METHODS
    # ===========================
    
    async def track_repository(self, repo_id: int):
        """Track a repository"""
        result = await self.api_request("POST", "/tracked-repositories", {
            "repository_id": repo_id
        })
        
        if "error" in result:
            self.error_message = result["error"]
        else:
            self.success_message = "Repository tracked successfully!"
    
    async def get_tracked_repositories(self):
        """Get user's tracked repositories"""
        result = await self.api_request("GET", "/tracked-repositories")
        
        if "error" not in result:
            return result.get("repositories", [])
        return []
    
    async def sync_repository(self, repo_id: int):
        """Sync repository data from GitHub"""
        result = await self.api_request("POST", f"/sync/{repo_id}")
        
        if "error" in result:
            self.error_message = result["error"]
        else:
            self.success_message = "Repository synced successfully!"
            # Refresh repository data
            await self.load_repo_details_by_id(repo_id)

    # ===========================
    # DASHBOARD ACTION
    # ===========================
    async def fetch_dashboard(self):
        """Akcija za preuzimanje dashboard podataka sa backend-a"""
        await self.load_dashboard_data()


    # ===========================
    # SEARCH FUNCTIONALITY
    # ===========================
    
    def set_search_query(self, query: str):
        """Set search query"""
        self.search_query = query
    
    async def search_repositories(self):
        """Search repositories"""
        self.is_loading_repos = True
        self.error_message = ""
        
        try:
            result = await self.api_request("GET", "/repositories", {
                "page": 1,
                "per_page": 20,
                "search": self.search_query
            })
            
            if "error" in result:
                self.error_message = result["error"]
            else:
                self.repos_list = result.get("repositories", [])
                
        except Exception as e:
            self.error_message = f"Error searching repositories: {str(e)}"
        finally:
            self.is_loading_repos = False