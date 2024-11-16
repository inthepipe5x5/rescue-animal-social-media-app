import time
import functools
from datetime import datetime, timedelta
from ratelimit import RateLimitException

from Project.core.constants import API_CALLS_PER_DAY, TIME_PERIOD, MAX_TRIES


def dynamic_rate_limit(func):
    """
    Decorator to dynamically manage API rate limiting.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls_made += 1

        for attempt in range(MAX_TRIES):
            try:
                result = func(*args, **kwargs)

                # Update total_results if available in the API response
                if hasattr(result, "get") and result.get("pagination"):
                    wrapper.total_results = result["pagination"].get(
                        "total_count", wrapper.total_results
                    )

                sleep_time = calculate_sleep_time(
                    wrapper.total_results, wrapper.calls_made
                )
                print(f"Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

                return result

            except RateLimitException:
                if attempt < MAX_TRIES - 1:
                    print(
                        f"Rate limit hit. Retrying in 60 seconds... (Attempt {attempt + 1}/{MAX_TRIES})"
                    )
                    time.sleep(60)
                else:
                    print("Max retries reached. Sleeping until rate limit reset...")
                    sleep_until_reset()

        raise Exception("Failed to make API call after maximum retries")

    wrapper.calls_made = 0
    wrapper.total_results = float(
        "inf"
    )  # Initialize with infinity, will be updated with actual count
    return wrapper


def calculate_sleep_time(total_results, calls_made, buffer_factor=1.1):
    """
    Calculates the dynamic sleep time based on API usage and limits.
    """
    remaining_calls = API_CALLS_PER_DAY - calls_made

    if remaining_calls <= 0:
        return sleep_until_reset()

    time_until_reset = get_time_until_reset()

    if calls_made >= total_results:
        return time_until_reset

    sleep_time = (time_until_reset / remaining_calls) * buffer_factor
    return max(1, min(sleep_time, 3600))  # Between 1 second and 1 hour


def get_time_until_reset():
    """
    Calculates the time until the next rate limit reset.
    """
    now = datetime.now()
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    return (next_reset - now).total_seconds()


def sleep_until_reset():
    """
    Sleeps until the next rate limit reset.
    """
    sleep_time = get_time_until_reset()
    print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds until reset.")
    time.sleep(sleep_time)
    return 0  # Return 0 as we've already slept
