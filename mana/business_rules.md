# Local content-community rules

These are expected behavior, not observations inferred from a passing run.
The application is a synthetic local test target, not a real social network.

## AUTH-01 — Authentication

Anonymous visits to `/feed` and `/publish` redirect to `/login`. Community APIs require a
valid login session and reject anonymous requests with 401. Synthetic accounts are
`admin / admin123` and `viewer / viewer123`; neither may be used for real services.
Both demo accounts can use community functions. Role labels are not a new RBAC promise.

## SESSION-01 — Sessions

The session identifier is opaque, expires and is revoked on logout. Setting a username as
the cookie value must not authenticate. Restarting the app invalidates sessions; users log in again.

## POST-01 — Title

Trim leading/trailing whitespace first. The resulting title must contain 1–50 characters.
Character counts use Unicode code points (including emoji), consistently in Python and the UI.
Blank and over-limit values are rejected without creating a post.

## POST-02 — Body

Trim first. Body text must contain 1–500 characters. A successful post can be found in the feed.

## TAGS-01 — Tags

Split on commas, trim each item, discard empty items and deduplicate exact values in first-seen order.

## MEDIA-01 — Real images

Images are optional. Only actual PNG/JPEG content with matching declared type is accepted.
Maximum input size is 2 MiB (2,097,152 bytes); maximum decoded size is 20,000,000 pixels.
Reject corrupt/oversized content. Store under server-generated names, strip metadata and render
the image in its post. A failed publish must not expose an orphan image resource.

## SEARCH-01 — Search matching

Search title, body and tags using case-insensitive substring matching. Empty query lists all posts.

## SEARCH-02 — Empty states

An empty feed says “暂无内容，发布第一条内容吧”. A query without matches says “没有找到匹配内容”.

## LIKE-01 — Like state

Like is a per-user toggle. One user's first click increments the count, the second decrements it.
The API count, visible count and button `aria-pressed` state must agree.

## COMMENT-01 — Comments

Trim first. Comment length must be 1–100 characters. Rejected comments do not change state.
Accepted comments appear immediately; API count, UI count and comment-list length must agree.

## PERSIST-01 — Content persistence

Content, images, likes and comments survive page refresh/navigation and application restart when
the same data directory is used. Browser refresh tests alone do not establish restart persistence.
Separate run data directories must not affect one another.

## CONTROL-01 — Test-only reset

Reset is unavailable in ordinary mode. In explicit test mode it requires the instance's control
credential and clears only that instance's content and stored media. Do not send this credential
through browser tools or store it in reusable step knowledge.

## INJECT-01 — Known-defect demonstration

In `comment_counter` mode, comments are saved while the count is intentionally not incremented.
This violates COMMENT-01. Tests must retain the failed business assertion; never change the
expected count to zero to make this mode pass. An outer check may verify that the defect was detected.
