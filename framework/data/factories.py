"""Small deterministic factories keep test intent readable."""

from framework.data.models import CommunityPostData, Credentials


def admin_credentials() -> Credentials:
    return Credentials(username="admin", password="admin123", role="admin")


def viewer_credentials() -> Credentials:
    return Credentials(username="viewer", password="viewer123", role="viewer")


def invalid_credentials() -> Credentials:
    return Credentials(username="unknown", password="wrong", role="none")


def ai_testing_post() -> CommunityPostData:
    return CommunityPostData(
        title="我的AI测试实践",
        content="用 Playwright MCP 生成可执行测试，并保留完整证据。",
        tags="AI测试, Playwright",
        comment="这是自动生成后的验证评论",
    )
