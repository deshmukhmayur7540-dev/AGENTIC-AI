"""GitHub repository URL validator for CourseAgentAI.

Provides rigorous, defense-in-depth URL structure validation, SSRF defense,
deceptive lookalike domain rejection, normalization, and optional API reachability verification.
"""

import ipaddress
import re
import urllib.parse
from typing import Any, Optional
from pydantic import BaseModel, Field

# GitHub username: 1-39 chars, alphanumeric or single hyphens, cannot start or end with hyphen
GITHUB_OWNER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")

# GitHub repository name: 1-100 chars, alphanumeric, hyphens, underscores, dots
GITHUB_REPO_REGEX = re.compile(r"^[a-zA-Z0-9._-]{1,100}$")


class GitHubValidationResult(BaseModel):
    """Structured result of GitHub URL validation."""
    is_valid: bool = Field(description="True if URL is structurally valid and accepted")
    error_message: Optional[str] = Field(default=None, description="Human-readable error explanation if invalid")
    owner: Optional[str] = Field(default=None, description="Extracted repository owner")
    repo: Optional[str] = Field(default=None, description="Extracted repository name (clean without .git)")
    normalized_url: Optional[str] = Field(default=None, description="Normalized canonical HTTPS URL")
    validation_status: str = Field(default="PASSED", description="PASSED, WARNING, or SYNTAX_ERROR")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed validation breakdown")


def validate_github_url(raw_url: str) -> GitHubValidationResult:
    """Validate and normalize a GitHub repository URL strictly.
    
    Guarantees:
    - Enforces HTTPS scheme only.
    - Strictly checks hostname is 'github.com' or 'www.github.com'.
    - Rejects deceptive lookalikes (e.g. g1thub.com, github.com.fake.org, github.co, github.io).
    - Rejects localhost, IPv4, IPv6, and private-network SSRF targets.
    - Rejects embedded credentials (e.g. user:pass@github.com).
    - Requires root repository path (/owner/repo) and rejects subpaths (/tree/main, /blob/master).
    - Validates GitHub username and repo naming conventions.
    - Normalizes URL consistently without trailing slashes or .git suffix.
    """
    if not raw_url or not isinstance(raw_url, str):
        return GitHubValidationResult(
            is_valid=False,
            error_message="Submission URL cannot be empty.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "EMPTY_URL"},
        )

    url_str = raw_url.strip()

    # Reject whitespace inside URL
    if re.search(r"\s", url_str):
        return GitHubValidationResult(
            is_valid=False,
            error_message="URL contains invalid whitespace characters.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "WHITESPACE_IN_URL"},
        )

    try:
        parsed = urllib.parse.urlsplit(url_str)
    except Exception as exc:
        return GitHubValidationResult(
            is_valid=False,
            error_message=f"Malformed URL: {exc}",
            validation_status="SYNTAX_ERROR",
            details={"reason": "PARSE_EXCEPTION", "exception": str(exc)},
        )

    # 1. Enforce HTTPS scheme
    if parsed.scheme.lower() != "https":
        if parsed.scheme.lower() in ("http", "git", "ssh", "file", "ftp"):
            msg = f"Unsupported URL scheme '{parsed.scheme}://'. Submissions must use secure HTTPS ('https://')."
        else:
            msg = f"Invalid URL scheme '{parsed.scheme}://'. Only secure 'https://' URLs are permitted."
        return GitHubValidationResult(
            is_valid=False,
            error_message=msg,
            validation_status="SYNTAX_ERROR",
            details={"reason": "INVALID_SCHEME", "scheme": parsed.scheme},
        )

    # 2. Reject embedded credentials (user:pass@...)
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return GitHubValidationResult(
            is_valid=False,
            error_message="URLs with embedded credentials (username/password) are strictly prohibited for security.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "EMBEDDED_CREDENTIALS"},
        )

    # 3. Hostname extraction & port check
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        host, port_str = netloc.split(":", 1)
        if port_str != "443":
            return GitHubValidationResult(
                is_valid=False,
                error_message=f"Non-standard HTTPS port ':{port_str}' is not permitted. Standard port 443 is required.",
                validation_status="SYNTAX_ERROR",
                details={"reason": "INVALID_PORT", "port": port_str},
            )
    else:
        host = netloc

    # 4. Localhost and IP address SSRF protection
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.endswith(".local"):
        return GitHubValidationResult(
            is_valid=False,
            error_message="Localhost and loopback addresses cannot be submitted as public repository URLs.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "LOCALHOST_TARGET", "host": host},
        )

    try:
        ip = ipaddress.ip_address(host)
        return GitHubValidationResult(
            is_valid=False,
            error_message="IP address targets are prohibited. Expected official 'github.com' domain.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "IP_TARGET", "is_private": ip.is_private},
        )
    except ValueError:
        pass  # host is a domain name, proceed

    # 5. Strict GitHub hostname check
    allowed_hosts = {"github.com", "www.github.com"}
    if host not in allowed_hosts:
        # Check if lookalike or deceptive
        if "github" in host:
            msg = f"Host '{host}' is a deceptive or lookalike domain. Submissions must reside on official 'github.com'."
        else:
            msg = f"Host '{host}' is not GitHub. Assignment submissions must be hosted on 'github.com'."
        return GitHubValidationResult(
            is_valid=False,
            error_message=msg,
            validation_status="SYNTAX_ERROR",
            details={"reason": "NON_GITHUB_HOST", "host": host},
        )

    # 6. Path validation
    path = parsed.path
    # Strip leading/trailing slashes for segment parsing
    clean_path = path.strip("/")
    if not clean_path:
        return GitHubValidationResult(
            is_valid=False,
            error_message="Missing repository path in GitHub URL. Format: https://github.com/<owner>/<repo>",
            validation_status="SYNTAX_ERROR",
            details={"reason": "MISSING_REPO_PATH"},
        )

    segments = clean_path.split("/")
    if len(segments) == 1:
        return GitHubValidationResult(
            is_valid=False,
            error_message=f"URL specifies user profile '{segments[0]}' but lacks a repository name.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "MISSING_REPO_NAME", "owner": segments[0]},
        )

    if len(segments) > 2:
        return GitHubValidationResult(
            is_valid=False,
            error_message=(
                "URL points to a repository subpath, branch, or file. "
                "The root repository URL is required (e.g. https://github.com/owner/repository)."
            ),
            validation_status="SYNTAX_ERROR",
            details={"reason": "SUBPATH_NOT_PERMITTED", "subpath": "/".join(segments[2:])},
        )

    owner = segments[0]
    repo_raw = segments[1]

    # Validate owner name
    if not GITHUB_OWNER_REGEX.match(owner):
        return GitHubValidationResult(
            is_valid=False,
            error_message=f"Invalid GitHub account name '{owner}'. Must be 1-39 alphanumeric characters or hyphens.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "INVALID_OWNER_NAME", "owner": owner},
        )

    # Strip .git suffix if provided
    clean_repo = repo_raw[:-4] if repo_raw.endswith(".git") else repo_raw

    # Validate repo name
    if not clean_repo or not GITHUB_REPO_REGEX.match(clean_repo) or clean_repo in (".", ".."):
        return GitHubValidationResult(
            is_valid=False,
            error_message=f"Invalid GitHub repository name '{clean_repo}'.",
            validation_status="SYNTAX_ERROR",
            details={"reason": "INVALID_REPO_NAME", "repo": clean_repo},
        )

    normalized_url = f"https://github.com/{owner}/{clean_repo}"

    return GitHubValidationResult(
        is_valid=True,
        error_message=None,
        owner=owner,
        repo=clean_repo,
        normalized_url=normalized_url,
        validation_status="PASSED",
        details={
            "owner": owner,
            "repo": clean_repo,
            "normalized_url": normalized_url,
            "had_git_suffix": repo_raw.endswith(".git"),
        },
    )


async def check_remote_repository_access(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    timeout_seconds: float = 3.0,
) -> tuple[str, dict[str, Any]]:
    """Check remote GitHub repository access via public API safely.
    
    Guarantees:
    - Never throws unhandled network exceptions to caller.
    - Bounded execution with strict timeout (default 3s).
    - Distinguishes syntax validity from remote accessibility.
    - Sanitizes and never exposes credentials or private auth tokens in outputs.
    """
    import httpx

    api_url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    headers = {
        "User-Agent": "CourseAgentAI-AssignmentValidator/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            resp = await client.get(api_url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return "PASSED", {
                    "reachable": True,
                    "is_private": data.get("private", False),
                    "default_branch": data.get("default_branch", "main"),
                    "description": data.get("description"),
                    "updated_at": data.get("updated_at"),
                }
            elif resp.status_code == 404:
                return "WARNING", {
                    "reachable": False,
                    "status_code": 404,
                    "note": (
                        "Repository is not publicly visible via GitHub API. "
                        "If this is a private solution repository, verify that faculty access has been granted."
                    ),
                }
            elif resp.status_code == 403:
                return "WARNING", {
                    "reachable": "UNVERIFIED",
                    "status_code": 403,
                    "note": "GitHub API rate limit exceeded or access restricted. URL syntax is valid and recorded.",
                }
            else:
                return "WARNING", {
                    "reachable": "UNVERIFIED",
                    "status_code": resp.status_code,
                    "note": f"GitHub returned HTTP status {resp.status_code}. URL syntax is valid and recorded.",
                }

    except httpx.TimeoutException:
        return "WARNING", {
            "reachable": "UNVERIFIED",
            "note": "Network timeout reaching GitHub API. URL syntax is valid and recorded.",
        }
    except Exception as exc:
        return "WARNING", {
            "reachable": "UNVERIFIED",
            "note": f"Network check bypassed: {str(exc)[:100]}. URL syntax is valid and recorded.",
        }
