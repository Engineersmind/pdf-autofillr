# chatbot/managed/__init__.py
"""
chatbot Managed PDF Service — private internal package, NOT part of the open source SDK.

This stub is included in the open source SDK so that imports fail with a clear,
actionable error rather than a generic AttributeError.

The managed filler uses Auth0 machine-to-machine tokens to authenticate against
your private PDF Lambda endpoint.  It is distributed as a separate private package
(chatbot-managed) that lives in its own repo alongside this SDK.

Install privately::

    pip install git+https://github.com/yourorg/chatbot-managed.git

Then wire it::

    from chatbot_managed.filler import chatbotManagedPDFFiller
    from chatbot import chatbotClient

    client = chatbotClient(
        ...,
        pdf_filler=chatbotManagedPDFFiller(
            auth0_domain=os.environ["AUTH0_DOMAIN"],
            auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
            auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
            auth0_audience=os.environ["AUTH0_AUDIENCE"],
            pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
            pdf_api_key=os.environ["PDF_API_KEY"],
        )
    )

Required environment variables for the managed filler::

    AUTH0_DOMAIN          your-tenant.us.auth0.com
    AUTH0_CLIENT_ID       ...
    AUTH0_CLIENT_SECRET   ...
    AUTH0_AUDIENCE        https://your-api-audience
    FILL_PDF_LAMBDA_URL   https://your-pdf-lambda-url.com
    PDF_API_KEY           ...
"""


def __getattr__(name):
    if name in ("chatbotManagedPDFFiller", "chatbotManagedConfig"):
        raise ImportError(
            f"{name} is not available in the open source chatbot SDK.\n"
            "\n"
            "This class lives in the private 'chatbot-managed' package.\n"
            "Install it from your internal repository:\n"
            "  pip install git+https://github.com/yourorg/chatbot-managed.git\n"
            "\n"
            "Then import directly from chatbot_managed, not from chatbot.managed:\n"
            "  from chatbot_managed.filler import chatbotManagedPDFFiller\n"
            "\n"
            "See the chatbot-managed repo README for setup instructions."
        )
    raise AttributeError(f"module 'chatbot.managed' has no attribute {name!r}")
