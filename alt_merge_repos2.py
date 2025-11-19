#!/usr/bin/env python3
"""
Git Repository Merger

Merges multiple git repositories into a single repository with path filtering,
branch preservation, and subdirectory organization.

This script:
1. Clones multiple repositories to temporary directories
2. Applies git filter-repo to filter paths in each repository
3. Moves repositories to subdirectories
4. Merges all repositories into a single output repository
5. Preserves specific branches from forks
6. Performs aggressive garbage collection

Usage:
    python alt_merge_repos2.py -c config.json -o output-repo
    python alt_merge_repos2.py -c config.toml -o output-repo --base-dir /path/to/work

Configuration File Format (JSON):
{
  "repositories": [
    {
      "name": "repo-name",
      "url": "git@github.com:org/repo.git",
      "default_branch": "master",
      "subdirectory": "optional-subdir",
      "filter_paths": ["path1", "path2"],
      "invert_paths": true,
      "branches_to_grab": [
        {"remote_url": "git@github.com:user/fork.git", "branch": "branch-name"}
      ],
      "reset_to_branch": "optional-branch",
      "preserve_files": ["file1", "file2"]
    }
  ],
  "final_remote": {
    "name": "github",
    "url": "git@github.com:org/repo.git"
  }
}

Configuration File Format (TOML):
[final_remote]
name = "github"
url = "git@github.com:org/repo.git"

[[repositories]]
name = "repo-name"
url = "git@github.com:org/repo.git"
default_branch = "master"
subdirectory = "optional-subdir"
filter_paths = ["path1", "path2"]
invert_paths = true
reset_to_branch = "optional-branch"
preserve_files = ["file1", "file2"]

[[repositories.branches_to_grab]]
remote_url = "git@github.com:user/fork.git"
branch = "branch-name"


## Real example

- `python alt_merge_repos2.py -c matisse-merge-config.json -o matisse-new [--base-dir /path/to/work]`
- `python alt_merge_repos2.py -c matisse-merge-config.toml -o matisse-new [--base-dir /path/to/work]`

### TOML:
```toml
[final_remote]
name = "github"
url = "git@github.com:analyzere/matisse.git"

[[repositories]]
name = "matisse-temp"
url = "git@github.com:analyzere/matisse-temp.git"
default_branch = "master"
filter_paths = [
    ".gitmodules",
    "arium-dashboards",
    "reinsurance-standalone",
    "adminpanel-starter"
]
invert_paths = true

[[repositories]]
name = "matisse-backend"
url = "git@github.com:analyzere/matisse-backend.git"
default_branch = "master"
subdirectory = "matisse-backend"
reset_to_branch = "okta"
filter_paths = ["src/main/java/are/"]
invert_paths = true

[[repositories.branches_to_grab]]
remote_url = "git@github.com:vgordeyev/matisse-backend.git"
branch = "ISSUE-172-pickup-existing-authors-as-users"

[[repositories]]
name = "matisse-frontend"
url = "git@github.com:analyzere/matisse-frontend.git"
default_branch = "master"
subdirectory = "matisse-frontend"
filter_paths = [
    "app/",
    "src/",
    "apps/cap/",
    "UserGuide.pdf",
    "data/",
    "q",
    "yarn.lock",
    "apps/reinsurance/src/app/layouts/test/programme-mock-data.ts",
    "apps/reinsurance/yarn.lock",
    "package-lock.json",
    "server-src",
    "Gruntfile.js",
    "webpack",
    "webpack.config.js",
    "webpack.common.config.js",
    "R-scripts",
    ".history",
    "test",
    "matisse-frontend/apps/reinsurance/src/app/shared/date-picker"
]
invert_paths = true
preserve_files = ["package-lock.json"]

[[repositories.branches_to_grab]]
remote_url = "git@github.com:cgerrie/matisse-frontend.git"
branch = "issue-103-chart-x-axis-options"

[[repositories.branches_to_grab]]
remote_url = "git@github.com:cgerrie/matisse-frontend.git"
branch = "issue-103-new-chart-calculation"

[[repositories.branches_to_grab]]
remote_url = "git@github.com:cgerrie/matisse-frontend.git"
branch = "issue-103-new-chart-x-axis-options"

[[repositories.branches_to_grab]]
remote_url = "git@github.com:UriiChe/matisse-frontend.git"
branch = "fix-linted-issues"
```
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    tomllib = None


class GitRepositoryMerger:
    """Handles merging multiple git repositories into one."""

    def __init__(
        self,
        config: dict[str, Any],
        output_repo: str,
        base_dir: Path,
        tmp_dir: Path,
    ):
        self.config = config
        self.output_repo = output_repo
        self.base_dir = base_dir
        self.tmp_dir = tmp_dir
        self.output_path = base_dir / output_repo
        self.git_args = ["--allow-unrelated-histories", "--no-edit"]

    def run_git(
        self, *args: str, cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=True,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Error running: {' '.join(cmd)}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            raise

    def info(self, message: str) -> None:
        """Print an info message."""
        print(f"Info: {message}")

    def warn(self, message: str) -> None:
        """Print a warning message."""
        print(f"Warning: {message}")

    def grab_remote(self, remote_url: str, branch_name: str, cwd: Path) -> None:
        """Grab a branch from a remote repository."""
        self.info(f"Grabbing branch '{branch_name}' from {remote_url}")
        try:
            self.run_git("remote", "add", "temp", remote_url, cwd=cwd)
            self.run_git("fetch", "temp", branch_name, cwd=cwd, check=False)
            result = self.run_git(
                "branch", branch_name, f"temp/{branch_name}", cwd=cwd, check=False
            )
            if result.returncode != 0:
                self.run_git(
                    "branch", "-f", branch_name, f"temp/{branch_name}", cwd=cwd
                )
            self.run_git("remote", "rm", "temp", cwd=cwd)
        except subprocess.CalledProcessError:
            self.warn(f"Failed to grab branch {branch_name} from {remote_url}")

    def create_branch(self, repo_path: Path, branch_name: str, cwd: Path) -> None:
        """Create a branch from a remote repository."""
        self.info(f"Creating branch '{branch_name}' from {repo_path}")
        # Try to checkout master/main, create if it doesn't exist
        for default_branch in ["master", "main"]:
            result = self.run_git(
                "checkout", "-q", default_branch, cwd=cwd, check=False
            )
            if result.returncode == 0:
                break
        else:
            self.run_git("checkout", "-q", "-b", "master", cwd=cwd)

        # Create or checkout the branch
        result = self.run_git("checkout", "-q", "-b", branch_name, cwd=cwd, check=False)
        if result.returncode != 0:
            self.run_git("checkout", "-q", branch_name, cwd=cwd)

        # Pull the branch
        self.run_git(
            "pull", str(repo_path), branch_name, *self.git_args, cwd=cwd, check=False
        )

        # Return to master/main
        for default_branch in ["master", "main"]:
            result = self.run_git(
                "checkout", "-q", default_branch, cwd=cwd, check=False
            )
            if result.returncode == 0:
                break
        else:
            self.run_git("checkout", "-q", "-b", "master", cwd=cwd)

    def clone_repo(self, repo_url: str, repo_name: str) -> Path:
        """Clone a repository to temporary directory."""
        tmp_repo = self.tmp_dir / repo_name
        self.info(f"Cloning {repo_name} from {repo_url}")

        if tmp_repo.exists():
            shutil.rmtree(tmp_repo)

        self.run_git("clone", repo_url, str(tmp_repo))
        return tmp_repo

    def apply_filter(
        self,
        filter_paths: list[str],
        invert_paths: bool,
        cwd: Path,
    ) -> None:
        """Apply git filter-repo with path filtering."""
        if not filter_paths:
            return

        self.info(
            f"Applying filter-repo with {len(filter_paths)} path(s), invert={invert_paths}"
        )

        filter_args = []
        for path in filter_paths:
            filter_args.extend(["--path", path])

        if invert_paths:
            filter_args.append("--invert-paths")

        filter_args.append("--force")
        self.run_git("filter-repo", *filter_args, cwd=cwd)

    def process_repository(self, repo_config: dict[str, Any]) -> Path:
        """Process a single repository from configuration."""
        repo_name = repo_config.get("name")
        repo_url = repo_config.get("url")
        default_branch = repo_config.get("default_branch", "master")
        subdirectory = repo_config.get("subdirectory")
        filter_paths = repo_config.get("filter_paths", [])
        invert_paths = repo_config.get("invert_paths", False)
        branches_to_grab = repo_config.get("branches_to_grab", [])
        reset_to_branch = repo_config.get("reset_to_branch")
        preserve_files = repo_config.get("preserve_files", [])

        if not repo_name or not repo_url:
            raise ValueError("Repository configuration missing 'name' or 'url'")

        self.info(f"Processing repository: {repo_name}")

        # Clone repository
        tmp_repo = self.clone_repo(repo_url, repo_name)

        # Reset to specific branch if requested
        if reset_to_branch:
            self.info(f"Resetting to branch: {reset_to_branch}")
            result = self.run_git(
                "reset",
                "--hard",
                f"origin/{reset_to_branch}",
                cwd=tmp_repo,
                check=False,
            )
            if result.returncode != 0:
                self.warn(f"Failed to reset to {reset_to_branch}")

        # Grab branches from forks
        for branch_config in branches_to_grab:
            remote_url = branch_config.get("remote_url")
            branch_name = branch_config.get("branch")
            if remote_url and branch_name:
                self.grab_remote(remote_url, branch_name, tmp_repo)

        # Preserve files before filtering
        preserve_dir = self.tmp_dir / f"preserve_{repo_name}"
        if preserve_dir.exists():
            shutil.rmtree(preserve_dir)
        preserve_dir.mkdir(parents=True, exist_ok=True)

        for file_path in preserve_files:
            source_file = tmp_repo / file_path
            if source_file.is_file():
                self.info(f"Preserving file: {file_path}")
                shutil.copy2(source_file, preserve_dir / source_file.name)

        # Apply path filtering
        if filter_paths:
            self.apply_filter(filter_paths, invert_paths, tmp_repo)

        # Move to subdirectory if specified
        if subdirectory:
            self.info(f"Moving repository to subdirectory: {subdirectory}")
            self.run_git(
                "filter-repo",
                "--to-subdirectory-filter",
                subdirectory,
                "--force",
                cwd=tmp_repo,
            )

        # Restore preserved files
        if preserve_dir.exists() and any(preserve_dir.iterdir()):
            for preserved_file in preserve_dir.iterdir():
                if preserved_file.is_file():
                    if subdirectory:
                        target_path = tmp_repo / subdirectory / preserved_file.name
                    else:
                        target_path = tmp_repo / preserved_file.name

                    self.info(
                        f"Restoring preserved file: {target_path.relative_to(tmp_repo)}"
                    )
                    shutil.copy2(preserved_file, target_path)
                    self.run_git(
                        "add", str(target_path.relative_to(tmp_repo)), cwd=tmp_repo
                    )

            # Check if there are changes to commit
            result = self.run_git("status", "--porcelain", cwd=tmp_repo, check=False)
            if result.stdout.strip():
                self.run_git(
                    "commit", "-m", "Restore preserved files", cwd=tmp_repo, check=False
                )

            shutil.rmtree(preserve_dir)

        return tmp_repo

    def make_new_repo(self) -> None:
        """Create the merged repository."""
        # Initialize new repository
        self.info(f"Initializing new repository at: {self.output_path}")
        if self.output_path.exists():
            shutil.rmtree(self.output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.run_git("init", cwd=self.output_path)

        # Process each repository
        repositories = self.config.get("repositories", [])
        processed_repos: list[tuple[Path, dict[str, Any]]] = []

        for repo_config in repositories:
            tmp_repo = self.process_repository(repo_config)
            processed_repos.append((tmp_repo, repo_config))

        # Merge repositories in order
        self.info("Merging repositories into final repository")

        for tmp_repo, repo_config in processed_repos:
            repo_name = tmp_repo.name
            default_branch = repo_config.get("default_branch", "master")

            self.info(f"Pulling {repo_name} (branch: {default_branch})")
            self.run_git(
                "pull",
                str(tmp_repo),
                default_branch,
                *self.git_args,
                cwd=self.output_path,
                check=False,
            )

            # Create branches for grabbed branches
            branches_to_grab = repo_config.get("branches_to_grab", [])
            for branch_config in branches_to_grab:
                branch_name = branch_config.get("branch")
                if branch_name:
                    self.create_branch(tmp_repo, branch_name, self.output_path)

        # Add final remote if specified
        final_remote = self.config.get("final_remote")
        if final_remote:
            remote_name = final_remote.get("name")
            remote_url = final_remote.get("url")
            if remote_name and remote_url:
                self.info(f"Adding remote '{remote_name}': {remote_url}")
                self.run_git(
                    "remote",
                    "add",
                    remote_name,
                    remote_url,
                    cwd=self.output_path,
                    check=False,
                )

    def aggressive_gc(self) -> None:
        """Perform aggressive garbage collection."""
        self.info("Performing aggressive garbage collection")
        # Delete references to the old history
        result = self.run_git(
            "for-each-ref",
            "--format=delete %(refname)",
            "refs/original",
            cwd=self.output_path,
            check=False,
        )
        if result.stdout.strip():
            subprocess.run(
                ["git", "update-ref", "--stdin"],
                input=result.stdout,
                cwd=self.output_path,
                text=True,
                check=False,
            )

        # Flag all deleted objects for garbage collection
        self.run_git("reflog", "expire", "--expire=now", "--all", cwd=self.output_path)
        # Garbage collect
        self.run_git("gc", "--prune=now", cwd=self.output_path)

    def run(self) -> None:
        """Run the complete merge process."""
        self.info("Starting repository merge process")
        self.info(f"Output: {self.output_path}")
        self.info(f"Temp directory: {self.tmp_dir}")

        self.make_new_repo()
        self.aggressive_gc()

        # Check for git-big-files if available
        result = shutil.which("git-big-files")
        if result:
            self.info("Analyzing large files")
            try:
                subprocess.run(
                    ["git-big-files"],
                    cwd=self.output_path,
                    check=False,
                )
            except Exception:
                pass

        self.info("Repository merge complete!")
        # Get disk usage
        du_result = subprocess.run(
            ["du", "-sh", str(self.output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if du_result.returncode == 0:
            print(f"DISK USAGE: {du_result.stdout.strip()}")
        print(f"Repository location: {self.output_path}")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from JSON or TOML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    suffix = config_path.suffix.lower()
    if suffix == ".json":
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    elif suffix == ".toml":
        if tomllib is None:
            raise ImportError("TOML support requires Python 3.11+ or tomli package")
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    else:
        raise ValueError(
            f"Unsupported config file format: {suffix}. Use .json or .toml"
        )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Merge multiple git repositories into a single repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Path to JSON or TOML configuration file",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output repository directory name",
    )
    parser.add_argument(
        "-b",
        "--base-dir",
        type=Path,
        default=Path.home(),
        help=f"Base directory to work in (default: {Path.home()})",
    )
    parser.add_argument(
        "-t",
        "--tmp-dir",
        type=Path,
        default=Path("/tmp"),
        help="Temporary directory for clones (default: /tmp)",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        merger = GitRepositoryMerger(
            config=config,
            output_repo=args.output,
            base_dir=args.base_dir,
            tmp_dir=args.tmp_dir,
        )
        merger.run()
    except (
        FileNotFoundError,
        ValueError,
        ImportError,
        subprocess.CalledProcessError,
    ) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
