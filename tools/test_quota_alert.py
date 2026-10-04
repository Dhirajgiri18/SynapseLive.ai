from app import llm


class FakeModels:
    def __init__(self):
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        raise RuntimeError(
            "429 RESOURCE_EXHAUSTED 'quotaId': "
            "'GenerateRequestsPerDayPerProjectPerModel-FreeTier' "
            "'retryDelay': '55008s'"
        )


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def main() -> None:
    original_api_key = llm.GEMINI_API_KEY
    original_client = llm._client
    fake_client = FakeClient()
    llm.GEMINI_API_KEY = "test-only-key"
    llm._client = fake_client
    llm.reset_quota_state()
    try:
        for attempt in (1, 2):
            try:
                llm.generate("hi", chain=("test-model",))
            except llm.QuotaExhausted as error:
                print(attempt, llm.describe_quota(error))
            else:
                raise AssertionError("Expected a daily-quota exception")

        if fake_client.models.calls != 1:
            raise AssertionError(
                f"Expected one fake API call, got {fake_client.models.calls}"
            )
        print("Second request failed fast without another API call.")
    finally:
        llm.reset_quota_state()
        llm.GEMINI_API_KEY = original_api_key
        llm._client = original_client


if __name__ == "__main__":
    main()
