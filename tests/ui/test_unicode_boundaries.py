import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.models import CommunityPostData
from framework.pages.publish_page import PublishPage


@pytest.mark.ui
@pytest.mark.regression
def test_emoji_counts_match_the_server_and_overlimit_is_rejected(
    authenticated_page: Page, settings: Settings
) -> None:
    publish = PublishPage(authenticated_page, settings.base_url).open()
    data = CommunityPostData(title="😀" * 50, content="body", tags="unicode", comment="ok")
    publish.fill(data).publish().expect_success()
    expect(authenticated_page.locator("#title-count")).to_have_text("50/50")
    publish.title.fill("😀" * 51)
    publish.publish()
    expect(publish.error).to_have_text("Title must not exceed 50 characters")
    assert authenticated_page.request.get(f"{settings.api_url}/api/posts").json()["total"] == 1
