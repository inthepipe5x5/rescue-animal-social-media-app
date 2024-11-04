#API exceptions for HTTP requests to PetFinder

from requests.exceptions import HTTPError #TODO: figure out if combining HTTPError & werkzeug.exceptions is the direction I want
from werkzeug.exceptions import (
    HTTPException,
    Unauthorized,
    Forbidden,
    BadRequest,
    NotFound,
    MethodNotAllowed,
    RequestTimeout,
    Gone,
)
from ratelimit import RateLimitException, sleep_and_retry

# api_exceptions.py

from requests.exceptions import HTTPError
from werkzeug.exceptions import (
    HTTPException,
    Unauthorized,
    Forbidden,
    BadRequest,
    NotFound,
    MethodNotAllowed,
    RequestTimeout,
    Gone,
)

"""
Custom exceptions for PetFinderAPIError




"""
class PetFinderAPIError(HTTPError, HTTPException):
    """Base class for PetFinder API errors."""
    default_message = "An unknown error occurred."
    status_code = 500

    def __init__(self, error_title="Error", error_subtitle="", error_message="", redirect_url="/"):
        self.error_title = error_title
        self.error_subtitle = error_subtitle
        self.error_message = error_message
        self.redirect_url = redirect_url
        
    def __str__(self):
        return f"{self.message} (Status Code: {self.status_code})"
    
    def error_info(self):
        # The comment `"""Return dict of error info attributes"""` is providing a brief description or
        # documentation for the `error_info` method in the `PetFinderAPIError` class. It explains that
        # the purpose of the method is to return a dictionary containing the error information
        # attributes such as error title, subtitle, message, redirect URL, and redirect text. This
        # comment serves as a helpful guide for anyone reading or working with the code to understand
        # the functionality of the `error_info` method.
        
        """Return dict of error info attributes
        """
        return {
        "error_title" :self.error_title,
        "error_subtitle" :self.error_subtitle,
        "error_message" :self.error_message,
        "redirect_url" :self.redirect_url,
        "redirect_text" :self.redirect_text,
        }

class PetFinderInvalidCredentialsError(PetFinderAPIError, Unauthorized):
    """Raised when access is denied due to invalid API credentials."""
    def __init__(self, error_message="Invalid credentials provided"):
        super().__init__(error_title="Authorization Error", error_subtitle="Invalid Credentials", error_message=error_message)



class PetFinderAccessDeniedError(PetFinderAPIError, Forbidden):
    """Raised when access is denied due to insufficient permissions."""
    def __init__(self, invalid_params, error_message="One or more parameters are invalid"):
        self.invalid_params = invalid_params
        super().__init__(error_title="Invalid Parameters", error_subtitle="Invalid request parameters", error_message=error_message)



class PetFinderResourceNotFoundError(PetFinderAPIError, Gone):
    """Raised when a resource is not found."""
    def __init__(self, error_message="An unexpected server error occurred"):
        super().__init__(error_title="Server Error", error_subtitle="Unexpected error from PetFinder API", error_message=error_message)


class PetFinderInvalidMethod(PetFinderAPIError, MethodNotAllowed):
    """Raised when an invalid method is used on a route."""
    default_message = "Invalid HTTP method used."
    status_code = 405


class PetFinderUnexpectedServerError(PetFinderAPIError):
    """Raised for server errors."""
    default_message = "Server encountered an error."
    status_code = 500


class PetFinderInvalidParametersError(PetFinderAPIError, BadRequest):
    """Raised when a request contains invalid parameters."""
    default_message = "Invalid parameters were passed in the request."
    status_code = 400

    def __init__(self, message=None, invalid_params=None):
        super().__init__(message=message or self.default_message, status_code=self.status_code)
        self.invalid_params = set(invalid_params) if invalid_params else set()


class PetFinderLocationError(PetFinderAPIError, BadRequest):
    """Raised when the location cannot be determined."""
    default_message = "Location could not be determined."
    status_code = 400
