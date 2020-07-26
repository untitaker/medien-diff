import sentry_sdk


def tag_http_response(response):
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("status", response.status_code)
        scope.fingerprint = ["{{ default }}", response.status_code]
        scope.set_extra("response_content", response.content)
