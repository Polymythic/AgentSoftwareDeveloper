"""
GitHub integration client for the multi-agent system.
"""
import os
import logging
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from github import Github, GithubException
from github.Repository import Repository
from github.Branch import Branch
from github.PullRequest import PullRequest
from github.Commit import Commit

from shared.models import GitHubCommit, GitHubPR, AgentRole
from database.manager import db_manager

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub client for repository operations."""
    
    def __init__(self, token: str, agent_name: str, agent_role: AgentRole):
        """Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token
            agent_name: Name of the agent using this client
            agent_role: Role of the agent
        """
        self.token = token
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.github = Github(token)
        self.user = self.github.get_user()
        
        logger.info(f"GitHub client initialized for {agent_name} ({agent_role.value})")
    
    def get_repository(self, repo_name: str) -> Optional[Repository]:
        """Get a repository by name.
        
        Args:
            repo_name: Repository name (owner/repo)
            
        Returns:
            Repository object or None if not found
        """
        try:
            repo = self.github.get_repo(repo_name)
            logger.info(f"Retrieved repository: {repo_name}")
            return repo
        except GithubException as e:
            logger.error(f"Failed to get repository {repo_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            return None
    
    def create_branch(self, repo: Repository, base_branch: str, new_branch: str) -> Optional[Branch]:
        """Create a new branch from an existing branch.
        
        Args:
            repo: Repository object
            base_branch: Base branch name
            new_branch: New branch name
            
        Returns:
            Branch object or None if failed
        """
        try:
            # Get the base branch
            base_ref = repo.get_branch(base_branch)
            
            # Create new branch
            repo.create_git_ref(f"refs/heads/{new_branch}", base_ref.commit.sha)
            
            # Get the new branch
            new_branch_ref = repo.get_branch(new_branch)
            
            logger.info(f"Created branch {new_branch} from {base_branch}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="branch_created",
                details={
                    "repository": repo.full_name,
                    "base_branch": base_branch,
                    "new_branch": new_branch
                }
            )
            
            return new_branch_ref
            
        except GithubException as e:
            logger.error(f"Failed to create branch: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return None
    
    def create_file(self, repo: Repository, path: str, content: str, message: str, 
                   branch: str = "main") -> bool:
        """Create a new file in the repository.
        
        Args:
            repo: Repository object
            path: File path
            content: File content
            message: Commit message
            branch: Target branch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the file
            repo.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch
            )
            
            logger.info(f"Created file {path} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="file_created",
                details={
                    "repository": repo.full_name,
                    "path": path,
                    "branch": branch,
                    "message": message
                }
            )
            
            return True
            
        except GithubException as e:
            logger.error(f"Failed to create file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return False
    
    def update_file(self, repo: Repository, path: str, content: str, message: str, 
                   branch: str = "main") -> bool:
        """Update an existing file in the repository.
        
        Args:
            repo: Repository object
            path: File path
            content: New file content
            message: Commit message
            branch: Target branch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the current file
            file = repo.get_contents(path, ref=branch)
            
            # Update the file
            repo.update_file(
                path=path,
                message=message,
                content=content,
                sha=file.sha,
                branch=branch
            )
            
            logger.info(f"Updated file {path} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="file_updated",
                details={
                    "repository": repo.full_name,
                    "path": path,
                    "branch": branch,
                    "message": message
                }
            )
            
            return True
            
        except GithubException as e:
            logger.error(f"Failed to update file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating file: {e}")
            return False
    
    def delete_file(self, repo: Repository, path: str, message: str, 
                   branch: str = "main") -> bool:
        """Delete a file from the repository.
        
        Args:
            repo: Repository object
            path: File path
            message: Commit message
            branch: Target branch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the current file
            file = repo.get_contents(path, ref=branch)
            
            # Delete the file
            repo.delete_file(
                path=path,
                message=message,
                sha=file.sha,
                branch=branch
            )
            
            logger.info(f"Deleted file {path} from {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="file_deleted",
                details={
                    "repository": repo.full_name,
                    "path": path,
                    "branch": branch,
                    "message": message
                }
            )
            
            return True
            
        except GithubException as e:
            logger.error(f"Failed to delete file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_content(self, repo: Repository, path: str, branch: str = "main") -> Optional[str]:
        """Get the content of a file.
        
        Args:
            repo: Repository object
            path: File path
            branch: Branch name
            
        Returns:
            File content or None if not found
        """
        try:
            file = repo.get_contents(path, ref=branch)
            content = base64.b64decode(file.content).decode('utf-8')
            return content
        except GithubException as e:
            logger.error(f"Failed to get file content: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None
    
    def create_pull_request(self, repo: Repository, title: str, body: str, 
                          head_branch: str, base_branch: str = "main",
                          reviewers: Optional[List[str]] = None,
                          labels: Optional[List[str]] = None) -> Optional[PullRequest]:
        """Create a pull request.
        
        Args:
            repo: Repository object
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch
            reviewers: List of reviewer usernames
            labels: List of labels
            
        Returns:
            PullRequest object or None if failed
        """
        try:
            # Create the pull request
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            # Add reviewers if specified
            if reviewers:
                pr.add_to_reviewers(*reviewers)
            
            # Add labels if specified
            if labels:
                pr.add_to_labels(*labels)
            
            logger.info(f"Created pull request #{pr.number} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="pr_created",
                details={
                    "repository": repo.full_name,
                    "pr_number": pr.number,
                    "title": title,
                    "head_branch": head_branch,
                    "base_branch": base_branch,
                    "reviewers": reviewers or [],
                    "labels": labels or []
                }
            )
            
            return pr
            
        except GithubException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None
    
    def review_pull_request(self, repo: Repository, pr_number: int, 
                          body: str, event: str = "COMMENT",
                          comments: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Review a pull request.
        
        Args:
            repo: Repository object
            pr_number: Pull request number
            body: Review body
            event: Review event (APPROVE, REQUEST_CHANGES, COMMENT)
            comments: List of review comments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pr = repo.get_pull(pr_number)
            
            # Create the review
            review = pr.create_review(
                body=body,
                event=event,
                comments=comments or []
            )
            
            logger.info(f"Created review for PR #{pr_number} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="pr_reviewed",
                details={
                    "repository": repo.full_name,
                    "pr_number": pr_number,
                    "event": event,
                    "body": body[:100]  # Truncate for logging
                }
            )
            
            return True
            
        except GithubException as e:
            logger.error(f"Failed to review pull request: {e}")
            return False
        except Exception as e:
            logger.error(f"Error reviewing pull request: {e}")
            return False
    
    def merge_pull_request(self, repo: Repository, pr_number: int, 
                          merge_method: str = "merge") -> bool:
        """Merge a pull request.
        
        Args:
            repo: Repository object
            pr_number: Pull request number
            merge_method: Merge method (merge, squash, rebase)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pr = repo.get_pull(pr_number)
            
            # Merge the pull request
            pr.merge(merge_method=merge_method)
            
            logger.info(f"Merged PR #{pr_number} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="pr_merged",
                details={
                    "repository": repo.full_name,
                    "pr_number": pr_number,
                    "merge_method": merge_method
                }
            )
            
            return True
            
        except GithubException as e:
            logger.error(f"Failed to merge pull request: {e}")
            return False
        except Exception as e:
            logger.error(f"Error merging pull request: {e}")
            return False
    
    def get_pull_requests(self, repo: Repository, state: str = "open") -> List[PullRequest]:
        """Get pull requests from a repository.
        
        Args:
            repo: Repository object
            state: PR state (open, closed, all)
            
        Returns:
            List of pull requests
        """
        try:
            prs = repo.get_pulls(state=state)
            return list(prs)
        except GithubException as e:
            logger.error(f"Failed to get pull requests: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting pull requests: {e}")
            return []
    
    def get_commits(self, repo: Repository, branch: str = "main") -> List[Commit]:
        """Get commits from a branch.
        
        Args:
            repo: Repository object
            branch: Branch name
            
        Returns:
            List of commits
        """
        try:
            commits = repo.get_commits(sha=branch)
            return list(commits)
        except GithubException as e:
            logger.error(f"Failed to get commits: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []
    
    def get_issues(self, repo: Repository, state: str = "open") -> List[Any]:
        """Get issues from a repository.
        
        Args:
            repo: Repository object
            state: Issue state (open, closed, all)
            
        Returns:
            List of issues
        """
        try:
            issues = repo.get_issues(state=state)
            return list(issues)
        except GithubException as e:
            logger.error(f"Failed to get issues: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting issues: {e}")
            return []
    
    def create_issue(self, repo: Repository, title: str, body: str,
                    labels: Optional[List[str]] = None,
                    assignees: Optional[List[str]] = None) -> Optional[Any]:
        """Create an issue.
        
        Args:
            repo: Repository object
            title: Issue title
            body: Issue description
            labels: List of labels
            assignees: List of assignee usernames
            
        Returns:
            Issue object or None if failed
        """
        try:
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or []
            )
            
            logger.info(f"Created issue #{issue.number} in {repo.full_name}")
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="github",
                action="issue_created",
                details={
                    "repository": repo.full_name,
                    "issue_number": issue.number,
                    "title": title,
                    "labels": labels or [],
                    "assignees": assignees or []
                }
            )
            
            return issue
            
        except GithubException as e:
            logger.error(f"Failed to create issue: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None
    
    def get_repository_stats(self, repo: Repository) -> Dict[str, Any]:
        """Get repository statistics.
        
        Args:
            repo: Repository object
            
        Returns:
            Dictionary with repository statistics
        """
        try:
            stats = {
                "name": repo.full_name,
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "size": repo.size,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "default_branch": repo.default_branch
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting repository stats: {e}")
            return {}
    
    def search_code(self, query: str, repo: Optional[str] = None) -> List[Any]:
        """Search for code in repositories.
        
        Args:
            query: Search query
            repo: Repository to search in (optional)
            
        Returns:
            List of search results
        """
        try:
            if repo:
                query = f"{query} repo:{repo}"
            
            results = self.github.search_code(query=query)
            return list(results)
            
        except GithubException as e:
            logger.error(f"Failed to search code: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching code: {e}")
            return [] 