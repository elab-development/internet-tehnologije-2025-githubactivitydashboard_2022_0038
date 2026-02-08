from github import Github, GithubException
from datetime import datetime, timedelta
from models import db, Repository, Activity, ActivityType
from config import Config
import logging

logger = logging.getLogger(__name__)

class GitHubAPI:
    def __init__(self, token=None):
        self.token = token or Config.GITHUB_TOKEN
        self.gh = Github(self.token) if self.token else Github()
    
    def get_repository_info(self, repo_full_name):
        """Fetch repository information from GitHub"""
        try:
            repo = self.gh.get_repo(repo_full_name)
            
            return {
                'github_id': repo.id,
                'name': repo.name,
                'full_name': repo.full_name,
                'owner': repo.owner.login,
                'url': repo.html_url,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'language': repo.language
            }
        except GithubException as e:
            logger.error(f"Error fetching repository {repo_full_name}: {e}")
            return None
    
    def fetch_recent_activities(self, repo_full_name, hours=24):
        """Fetch recent activities from a repository"""
        try:
            repo = self.gh.get_repo(repo_full_name)
            activities = []
            
            # Get recent commits
            try:
                for commit in repo.get_commits(since=datetime.now() - timedelta(hours=hours)):
                    activities.append({
                        'github_id': f"commit_{commit.sha}",
                        'activity_type': ActivityType.PUSH.value,
                        'actor': commit.author.login if commit.author else 'Unknown',
                        'action': 'pushed',
                        'ref': commit.commit.message[:100],
                        'timestamp': commit.commit.author.date,
                        'data': {
                            'sha': commit.sha,
                            'message': commit.commit.message,
                            'url': commit.html_url
                        }
                    })
            except Exception as e:
                logger.warning(f"Could not fetch commits for {repo_full_name}: {e}")
            
            # Get recent issues
            try:
                for issue in repo.get_issues(state='all', since=datetime.now() - timedelta(hours=hours)):
                    activity_type = ActivityType.ISSUE.value
                    if issue.pull_request:
                        activity_type = ActivityType.PULL_REQUEST.value
                    
                    activities.append({
                        'github_id': f"issue_{issue.id}",
                        'activity_type': activity_type,
                        'actor': issue.user.login,
                        'action': 'opened' if issue.state == 'open' else 'closed',
                        'ref': issue.title,
                        'timestamp': issue.created_at,
                        'data': {
                            'number': issue.number,
                            'title': issue.title,
                            'state': issue.state,
                            'url': issue.html_url
                        }
                    })
            except Exception as e:
                logger.warning(f"Could not fetch issues for {repo_full_name}: {e}")
            
            return activities
            
        except GithubException as e:
            logger.error(f"Error fetching activities for {repo_full_name}: {e}")
            return []
    
    def sync_repository(self, repo_full_name):
        """Sync repository data and activities with database"""
        # Get or create repository in database
        repo_info = self.get_repository_info(repo_full_name)
        if not repo_info:
            return None
        
        repository = Repository.query.filter_by(github_id=repo_info['github_id']).first()
        
        if repository:
            # Update existing repository
            for key, value in repo_info.items():
                if hasattr(repository, key):
                    setattr(repository, key, value)
            repository.last_updated = datetime.utcnow()
        else:
            # Create new repository
            repository = Repository(**repo_info)
            db.session.add(repository)
        
        db.session.commit()
        
        # Fetch and store recent activities
        activities_data = self.fetch_recent_activities(repo_full_name)
        
        for activity_data in activities_data:
            # Check if activity already exists
            existing = Activity.query.filter_by(github_id=activity_data['github_id']).first()
            
            if not existing:
                activity = Activity(
                    github_id=activity_data['github_id'],
                    activity_type=ActivityType(activity_data['activity_type']),
                    actor=activity_data['actor'],
                    action=activity_data['action'],
                    ref=activity_data['ref'],
                    timestamp=activity_data['timestamp'],
                    data=activity_data['data'],
                    repository_id=repository.id
                )
                db.session.add(activity)
        
        db.session.commit()
        
        return repository