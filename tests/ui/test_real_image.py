from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.data.models import CommunityPostData
from framework.pages.feed_page import FeedPage
from framework.pages.publish_page import PublishPage


@pytest.mark.ui
@pytest.mark.smoke
def test_uploaded_image_is_really_rendered(
    authenticated_page: Page, settings: Settings, tmp_path: Path
) -> None:
    image_path = tmp_path / "synthetic.png"
    Image.new("RGB", (64, 48), "navy").save(image_path)
    data = CommunityPostData(
        title="真实图片回归", content="验证上传与浏览器解码", tags="image", comment="checked"
    )
    PublishPage(authenticated_page, settings.base_url).open().fill(
        data, image_path
    ).publish().expect_success()
    feed = FeedPage(authenticated_page, settings.base_url).open().search_for(data.title)
    card = feed.expect_post(data.title, data.content)
    image = card.get_by_role("img", name=f"配图：{data.title}")
    expect(image).to_be_visible()
    expect(image).to_have_js_property("naturalWidth", 64)
    expect(image).to_have_js_property("naturalHeight", 48)
