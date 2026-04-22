"""
Basic usage of the PDF Autofiller SDK.

The mapper Lambda exposes three operations.  The typical flow is:

  1. make_embed_file  — extract fields from the PDF, map them, embed the result
  2. check_embed_file — (optional) verify the cache is ready before filling
  3. fill_pdf         — fill the embedded PDF with the user's actual data
"""

from pdf_autofiller import MapperClient
from pdf_autofiller.exceptions import AuthenticationError, MapperError

API_KEY = "your-api-key"   # the only thing customers need to set

USER_ID = 1
PDF_DOC_ID = 42
SESSION_ID = "session-abc123"
ENV = "prod"


def main():
    # function_url defaults to the production Lambda — no need to set it
    with MapperClient(api_key=API_KEY) as client:

        # ------------------------------------------------------------------
        # Step 1 — Extract, map, and embed the PDF
        # (run once per PDF; result is cached in S3 for subsequent fills)
        # ------------------------------------------------------------------
        print("Running make_embed_file ...")
        embed_result = client.make_embed_file(
            user_id=USER_ID,
            pdf_doc_id=PDF_DOC_ID,
            session_id=SESSION_ID,
            env=ENV,
        )
        print(f"  cache_hit : {embed_result.get('cache_hit')}")
        print(f"  result    : {embed_result}")

        # ------------------------------------------------------------------
        # Step 2 — Check the cache (useful if calling make_embed_file again)
        # ------------------------------------------------------------------
        print("\nRunning check_embed_file ...")
        check_result = client.check_embed_file(
            user_id=USER_ID,
            pdf_doc_id=PDF_DOC_ID,
            session_id=SESSION_ID,
            env=ENV,
        )
        print(f"  cache_hit : {check_result.get('cache_hit')}")

        # ------------------------------------------------------------------
        # Step 3 — Fill the PDF with user data
        # ------------------------------------------------------------------
        print("\nRunning fill_pdf ...")
        fill_result = client.fill_pdf(
            user_id=USER_ID,
            pdf_doc_id=PDF_DOC_ID,
            session_id=SESSION_ID,
            env=ENV,
        )
        print(f"  filled_pdf: {fill_result.get('filled_pdf')}")
        print(f"  result    : {fill_result}")


if __name__ == "__main__":
    try:
        main()
    except AuthenticationError as e:
        print(f"Auth error — check your API key: {e}")
    except MapperError as e:
        print(f"Mapper error: {e}")
