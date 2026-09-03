import allure
import pytest
from playwright.sync_api import Page

from framework.config.settings import Settings
from framework.data.factories import ai_testing_post
from framework.workflows.content_workflow import ContentLifecycleWorkflow


@allure.epic("AI-generated testing demo")
@allure.feature("Local content community")
@allure.story("Publish, search, like, and comment")
@pytest.mark.ui
@pytest.mark.smoke
def test_content_lifecycle(authenticated_page: Page, settings: Settings) -> None:
    with allure.step("Publish content, find it, like it, and add a comment"):
        workflow = ContentLifecycleWorkflow(authenticated_page, settings.base_url)
        workflow.publish_search_like_and_comment(ai_testing_post())
