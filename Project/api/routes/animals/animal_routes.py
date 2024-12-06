from flask import (
    Blueprint,
    current_app,
    flash,
    json,
    redirect,
    request,
    session,
    url_for,
    jsonify,
    render_template,
)
from urllib.parse import urljoin
from time import sleep
from Project.core.methods import (
    create_next_animal_url,
    get_location,
    default_session_dict,
    active_authenticated_user,
    current_user,
    create_init_params,
    get_anon_location,
    get_user_animal_preferences,
)
from Project.core.constants import (
    API_ANIMAL_TYPES_KEY,
    NEXT_ANIMAL_URLS_KEY,
    RESULTS_PER_PAGE_KEY,
)
import os
from dotenv import load_dotenv
from Project.services.petfinder.api_exceptions import PetFinderResourceNotFoundError
from Project.api.routes.data.data_routes import seed_animal_info
from Project.utils import Parse

from Project.services import pf as api

load_dotenv()

animals_bp = Blueprint(
    "animals", __name__, template_folder="templates", url_prefix="/animals"
)


@animals_bp.route("/discover/animals", methods=["GET"])
def discover_animals():
    """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

    user = current_user._get_current_object() if active_authenticated_user() else None

    # Determine user location
    location_data = None

    # Get location from user's serialized data
    location_data = user.serialize().get("location") if user else get_anon_location()
    if not location_data:
        return redirect(url_for("user.user_location_form"))

    init_params = create_init_params(req_type="animals")
    animal_types = (
        request.args.get("animal_type")
        or init_params.get("type")
        or user.get("animal_types")
        or session.get("ANIMAL_TYPES", ["dog"])
    )
    target_count = int(
        request.args.get("limit")
        or session.get(RESULTS_PER_PAGE_KEY)
        or init_params.get("limit", 9)
    )  # Number of animals per page

    # Prepare exclude_ids for viewed or favorited animals
    user_favorites = user.get_all_favorites if user else []
    viewed_content = session.get("VIEWED_CONTENT_LIST", [])
    exclude_ids = set(viewed_content + user_favorites)

    # Flatten user preferences for API request
    flattened_animal_preferences = (
        api.preprocess_preferences(
            init_params=init_params.copy(),
            prefs_obj=get_user_animal_preferences(species_list=animal_types),
        )
        if user
        else {animal_type: None for animal_type in animal_types}
    )

    # Ensure animal_types is always a list
    animal_types = [animal_types] if isinstance(animal_types, str) else animal_types

    next_urls = create_next_animal_url(animal_types=animal_types, endpoint="animals")

    render_content = []
    # try:

    while len(render_content) < target_count:
        session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session

        # Combine initial parameters with animal preferences and location if provided
        params = (
            init_params.copy().update(flattened_animal_preferences)
            if flattened_animal_preferences
            else init_params.copy()
        )

        # set params['location'] properly
        if location_data or isinstance(params.get("location"), (dict, object)):
            params["location"] = api.get_next_location(location_dict=location_data)

        for animal_type in animal_types:
            next_url = next_urls.get(animal_type) or urljoin(
                f"{api.BASE_API_URL}/animals", params
            )

            if not next_url:
                continue  # Skip this type if no next URL is available (exhausted)
            # Fetch data from the API using request_with_retry
            results = api.request_with_retry(
                endpoint="animals", request_url=next_url, params=params
            )

        if not results:
            raise PetFinderResourceNotFoundError()
            break  # Exit if generator returns no content

        # Filter and parse results
        filters = pf()
        filtered_results, success_flag = api.filter_parse_animal_results(
            results, filter_prefs=filters
        )
        render_content.extend(filtered_results)

        # Add viewed content to session if successful
        if success_flag:
            session["VIEWED_CONTENT_LIST"] = list(
                set(
                    session.get("VIEWED_CONTENT_LIST", [])
                    + [result["id"] for result in filtered_results]
                )
            )
            break

    # No content message
    if len(render_content) == 0:
        flash(
            "No animals found matching your filters. Adjust filters or try again later!",
            "warning",
        )
        init_params = {"limit": target_count}

        # Attempt backup API call if no content
        try:
            backup_results = api._get_request(
                "animals", f"{api.BASE_API_URL}/animals", params=init_params
            )
            if not backup_results:
                return redirect(
                    url_for(
                        "custom_error",
                        error_title="PetFinder API Unavailable",
                        error_subtitle="We're sorry for the inconvenience.",
                        error_message="PetFinder's API is temporarily down. Please try again later.",
                    )
                )
            render_content = backup_results.get("animals", [])
        except Exception as api_error:
            current_app.logger.error(f"API Backup Call Failed: {api_error}")
            return redirect(
                url_for(
                    "custom_error",
                    error_title="PetFinder API Error",
                    error_subtitle="Unable to retrieve animals.",
                    error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
                )
            )

        # except PetFinderAccessDeniedError as e:
        #         #wait attempt number of seconds in case of rate limiting
        #         sleep(int(attempt))
        #         #reset access token
        #         self._get_access_token()
        #         if attempt == max_retries:
        #             break
        #         else:
        #             continue
        #     except PetFinderInvalidParametersError as e:
        #         # Handle invalid parameters by removing problematic keys and retrying
        #         invalid_params = (
        #             e.invalid_params or []
        #         )  # Retrieve invalid params from error, if available
        #         for param in invalid_params:
        #             params.pop(param, None)  # Remove invalid key
        #         continue  # Retry request with modified parameters

        #     except PetFinderLocationError:
        #         # Handle location errors by cycling through alternative locations
        #         location_dict = params.get("location", {})
        #         while location_dict:
        #             next_location, location_dict = self.get_alternative_locations(
        #                 location_dict
        #             )

        #             if not next_location:
        #                 # All location alternatives have been exhausted; redirect user to enter location
        #                 return PetFinderLocationError(
        #                     error_title="Error determining location",
        #                     error_subtitle="Please set your location",
        #                     error_message=(
        #                         "Can't determine your location for local content. "
        #                         "Please enter your location or enable geolocation for more accurate results."
        #                     ),
        #                     redirect_url="/users/location",
        #                 ).error_info()

        #             # Update params with the new location and retry request
        #             params["location"] = next_location
        #             response = self._get_request(
        #                 endpoint,
        #                 request_url or f"{self.BASE_API_URL}/{endpoint}",
        #                 params=params,
        #             )
        #             self.log_and_raise_for_status(response)
        #             return response.json()  # Return if successful

        #     except RateLimitException:
        #         print("Rate limit reached. Retrying...")

        # # If max retries without success, raise a final error
        # raise Exception(f"Request to {endpoint} failed after {max_retries} retries.")

        # Respond with JSON for AJAX or render HTML
        if request.is_json:
            return jsonify(
                {"results": render_content, "success_flag": bool(render_content)}
            )

        return render_template("results.html", animals=render_content)

    # except Exception as e:
    #     current_app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
    #     return redirect(
    #         url_for(
    #             "custom_error",
    #             error_title="Unexpected Error",
    #             error_subtitle="We ran into an issue!",
    #             error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
    #         )
    #     )


# @animals_bp.route("/discover/animals", methods=["GET"])
# def discover_animals():
#     """Route to fetch and display paginated animal data, with error handling and fallback UI in case of API downtime."""

#     user = current_user._get_current_object() if active_authenticated_user() else None

#     # Determine user location
#     location_data = None
#     if user:
#         # Get location from user's serialized data
#         location_data = user.serialize().get("location")
#     else:
#         # Anonymous user, pull location from session
#         location_data = {
#             "city": session.get("city"),
#             "state": session.get("state"),
#             "postal_code": session.get("postal_code"),
#             "geolocation": session.get("geolocation"),
#         } or default_session_dict.get(DEFAULT_LOCATION)

#     init_params = create_init_params(req_type="animals")
#     animal_types = (
#         request.args.get("animal_type")
#         or init_params.get("type")
#         or user.get("animal_types")
#         or session.get("ANIMAL_TYPES", ["dog"])
#     )
#     target_count = int(
#         request.args.get("limit") or init_params.get("limit", 9)
#     )  # Number of animals per page

#     # Prepare exclude_ids for viewed or favorited animals
#     user_favorites = user.get_all_favorites if user else []
#     viewed_content = session.get("VIEWED_CONTENT_LIST", [])
#     exclude_ids = set(viewed_content + user_favorites)

#     # Flatten user preferences for API request
#     flattened_animal_preferences = (
#         api.preprocess_preferences(
#             init_params=init_params.copy(),
#             prefs_obj=get_user_animal_preferences(species_list=animal_types),
#         )
#         if user
#         else {animal_type: None for animal_type in animal_types}
#     )

#     # Ensure animal_types is always a list
#     animal_types = [animal_types] if isinstance(animal_types, str) else animal_types
#     next_urls = session.get(
#         NEXT_ANIMAL_URLS_KEY, {animal_type: None for animal_type in animal_types}
#     )

#     # Initialize generator with new parameters, including location
#     generator = api.animal_pagination_generator(
#         animal_types=animal_types,
#         target_count=target_count,
#         init_params=init_params,
#         next_urls=next_urls,
#         exclude_ids=exclude_ids,
#         flattened_animal_preferences=flattened_animal_preferences,
#         location_dict=location_data,
#     )

#     render_content = []
#     no_api_content = False

#     try:
#         for data in generator:
#             if "error" in data:
#                 # Flash the error message
#                 flash(
#                     f"Error fetching data for {data['animal_type']}: {data['error']}",
#                     "error",
#                 )
#                 # Optionally, animals_bpend partial results if desired
#                 render_content.extend(data.get("partial_results", []))
#             else:
#                 # Accumulate full results
#                 render_content.extend(data)

#         while len(render_content) < target_count:
#             results, next_urls = next(generator)
#             session[NEXT_ANIMAL_URLS_KEY] = next_urls  # Save updated next URLs in session

#             if not results:
#                 no_api_content = True
#                 break  # Exit if generator returns no content

#             # Filter and parse results
#             filters = create_user_preference_filters()
#             filtered_results, success_flag = api.filter_parse_animal_results(
#                 results, filter_prefs=filters
#             )
#             render_content.extend(filtered_results)

#             # Add viewed content to session if successful
#             if success_flag:
#                 session["VIEWED_CONTENT_LIST"] = list(
#                     set(
#                         session.get("VIEWED_CONTENT_LIST", [])
#                         + [result["id"] for result in filtered_results]
#                     )
#                 )
#                 break

#         # No content message
#         if no_api_content:
#             flash(
#                 "No animals found matching your filters. Adjust filters or try again later!",
#                 "warning",
#             )
#             init_params = {"limit": target_count}

#             # Attempt backup API call if no content
#             try:
#                 backup_results = api._get_request(
#                     "animals", f"{api.BASE_API_URL}/animals", params=init_params
#                 )
#                 if not backup_results:
#                     return redirect(
#                         url_for(
#                             "custom_error",
#                             error_title="PetFinder API Unavailable",
#                             error_subtitle="We're sorry for the inconvenience.",
#                             error_message="PetFinder's API is temporarily down. Please try again later.",
#                         )
#                     )
#                 render_content = backup_results.get("animals", [])
#             except Exception as api_error:
#                 current_app.logger.error(f"API Backup Call Failed: {api_error}")
#                 return redirect(
#                     url_for(
#                         "custom_error",
#                         error_title="PetFinder API Error",
#                         error_subtitle="Unable to retrieve animals.",
#                         error_message="Our system is currently experiencing issues connecting to PetFinder. Please try again later.",
#                     )
#                 )

#         # Respond with JSON for AJAX or render HTML
#         if request.is_json:
#             return jsonify(
#                 {"results": render_content, "success_flag": bool(render_content)}
#             )

#         return render_template("results.html", animals=render_content)

#     except Exception as e:
#         current_app.logger.error(f"Error at endpoint {request.endpoint}: {e}")
#         return redirect(
#             url_for(
#                 "custom_error",
#                 error_title="Unexpected Error",
#                 error_subtitle="We ran into an issue!",
#                 error_message="Our system encountered an issue loading animals. Please try refreshing the page or come back later.",
#             )
#         )


@animals_bp.route("/discover/animals/<animal_type>")
def discover_specific_animal_type(animal_type):

    types_list = session.get(API_ANIMAL_TYPES_KEY) or json.loads(
        os.environ.get(API_ANIMAL_TYPES_KEY, "[]")
    )

    # Validate animal_type
    if not types_list:
        # Make request to seed animal_types
        seed_animal_info()
        # Retry request to route
        return redirect(
            url_for("discover_specific_animal_type", animal_type=animal_type)
        )

    prettified_animal_type = Parse.prettify_animal_types(animal_type)

    if (animal_type, prettified_animal_type) not in types_list:
        return redirect(
            url_for(
                "custom_error",
                error_subtitle="Invalid Animal Type",
                error_title="Something went wrong...",
                error_message=f"Woops, we can't find that kind of animal to rescue...yet! {api.animal_emojis}",
            )
        )

    try:
        params = {
            "type": prettified_animal_type,
            "location": get_location(),
        }

        response = api.request_with_retry(
            endpoint="animals",
            request_url=urljoin(api.BASE_API_URL, "animals"),
            params=params,
        )

        data = api.log_and_raise_for_status(response) if response else None

        return jsonify({"results": data})
    except Exception as e:
        current_app.logger.error(f"{request.url} error: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred."}), 500


@animals_bp.route("/test/animals")
def test_animals():
    """Endpoint to retrieve data from PetFinder /animals route"""
    response = api.request_with_retry(
        request_url=urljoin(api.BASE_API_URL, "animals"),
        params={},
        endpoint="animals",
        max_retries=3,
    )
    data = response.json() or []
    return jsonify({"response": data})


@animals_bp.route("/test/animals/locations")
def test_location_animals():
    """TEST ROUTE TO TEST DIFFERENT COMBINATIONS OF PARAMS ACCEPTED BY PETFINDER API LOCATION PARAMS"""

    def fetch_data(location_str):
        params = {"location": location_str}
        response = api.request_with_retry(
            request_url=urljoin(api.BASE_API_URL, "animals"),
            params=params,
            endpoint="animals",
        )

        data = api.log_and_raise_for_status(response) if response else None
        return data, response.status_code if response else None

    location_dict = session.get("location", {}) or default_session_dict.get(
        "DEFAULT_LOCATION"
    )
    location_combinations = api.generate_location_combinations(location_dict)

    successful_combinations = []
    unsuccessful_combinations = []
    try:
        for key, value in location_combinations.items():
            sleep(3)
            data, status_code = fetch_data(value)
            if status_code in [200, 201] and data:
                successful_combinations.animals.append({key: value})
            else:
                unsuccessful_combinations.animals.append({key: value})

        return jsonify(
            {
                "successful_combinations": successful_combinations,
                "unsuccessful_combinations": unsuccessful_combinations,
            }
        )

    except Exception as e:
        current_app.logger.error(f"{request.url} error: {e}", exc_info=1)
        if "successful_combinations" in locals():
            successful_combinations = locals().get("successful_combinations", None)
            unsuccessful_combinations = locals().get("unsuccessful_combinations", None)
        return jsonify(
            {
                "successful_combinations": (
                    successful_combinations if successful_combinations else []
                ),
                "unsuccessful_combinations": (
                    unsuccessful_combinations if unsuccessful_combinations else []
                ),
            }
        )
