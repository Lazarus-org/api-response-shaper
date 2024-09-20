from .types import (
    MessageType,
    ErrorType,
    DataType,
    PageNumber,
    LinksType,
    TotalItems,
    TotalPages,
    TokenType,
    UserType,
    ProcessingTime,
)
from typing import Dict, List, Optional
from rest_framework.response import Response
from django.utils import timezone


# API Response Functions

def api_response(success: bool = True, message: MessageType = None, data: DataType = None, 
                 errors: ErrorType = None, status_code: int = 200) -> Response:
    """
    Constructs a standard API response structure.
    
    :param success: Indicates whether the request was successful.
    :param message: A message describing the result.
    :param data: Data to be returned in the response.
    :param errors: Any errors to include in the response.
    :param status_code: HTTP status code for the response.
    :return: A Response object with the structured response.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "data": data,
        "errors": errors,
    }
    return Response(response_structure, status=status_code)


def paginated_api_response(success: bool = True, message: MessageType = None, data: DataType = None, 
                           errors: ErrorType = None, status_code: int = 200, page: PageNumber = None, 
                           total_pages: TotalPages = None, total_items: TotalItems = None) -> Response:
    """
    Constructs a paginated API response structure.
    
    :param success: Indicates whether the request was successful.
    :param message: A message describing the result.
    :param data: Paginated data to be returned.
    :param errors: Any errors to include in the response.
    :param status_code: HTTP status code for the response.
    :param page: Current page number.
    :param total_pages: Total number of pages.
    :param total_items: Total number of items across all pages.
    :return: A Response object with the structured response.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "data": data,
        "errors": errors,
        "pagination": {
            "page": page,
            "total_pages": total_pages,
            "total_items": total_items,
        }
    }
    return Response(response_structure, status=status_code)


def error_api_response(message: MessageType = None, errors: ErrorType = None, error_code: Optional[str] = None, 
                       status_code: int = 400) -> Response:
    """
    Constructs an error response structure.
    
    :param message: Error message.
    :param errors: Detailed errors.
    :param error_code: Optional error code.
    :param status_code: HTTP status code for the response.
    :return: A Response object with the error structure.
    """
    response_structure = {
        "status": "error",
        "message": message,
        "error_code": error_code,
        "errors": errors,
    }
    return Response(response_structure, status=status_code)


def minimal_success_response(message: str = "Request successful", status_code: int = 200) -> Response:
    """
    Constructs a minimal success response without any additional data.
    
    :param message: Success message.
    :param status_code: HTTP status code for the response.
    :return: A Response object with the minimal success structure.
    """
    response_structure = {
        "status": "success",
        "message": message,
    }
    return Response(response_structure, status=status_code)


def metadata_api_response(success: bool = True, message: MessageType = None, data: DataType = None, 
                          errors: ErrorType = None, status_code: int = 200, processing_time: ProcessingTime = None, 
                          api_version: str = "1.0") -> Response:
    """
    Constructs a response structure with additional metadata, such as processing time and API version.
    
    :param success: Indicates whether the request was successful.
    :param message: A message describing the result.
    :param data: Data to be returned.
    :param errors: Any errors to include.
    :param status_code: HTTP status code.
    :param processing_time: Time taken to process the request.
    :param api_version: The version of the API.
    :return: A Response object with the metadata structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "data": data,
        "errors": errors,
        "meta": {
            "timestamp": timezone.now(),  # Current timestamp
            "processing_time": processing_time,
            "api_version": api_version,
        }
    }
    return Response(response_structure, status=status_code)


def hateoas_api_response(success: bool = True, message: MessageType = None, data: DataType = None, 
                         errors: ErrorType = None, status_code: int = 200, links: LinksType = None) -> Response:
    """
    Constructs a HATEOAS-compliant API response with related resource links.
    
    :param success: Indicates whether the request was successful.
    :param message: A message describing the result.
    :param data: Data to be returned.
    :param errors: Any errors to include.
    :param status_code: HTTP status code for the response.
    :param links: Dictionary of related resource links.
    :return: A Response object with the HATEOAS structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "data": data,
        "errors": errors,
        "links": links,
    }
    return Response(response_structure, status=status_code)


def multi_resource_response(success: bool = True, message: MessageType = None, resources: Optional[List[Dict]] = None, 
                            errors: ErrorType = None, status_code: int = 200) -> Response:
    """
    Constructs a response structure with multiple resources.
    
    :param success: Indicates whether the request was successful.
    :param message: A message describing the result.
    :param resources: List of resource data to be returned.
    :param errors: Any errors to include.
    :param status_code: HTTP status code.
    :return: A Response object with the multi-resource structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "resources": resources,
        "errors": errors,
    }
    return Response(response_structure, status=status_code)


def batch_api_response(success: bool = True, message: MessageType = None, results: Optional[List[Dict]] = None, 
                       errors: ErrorType = None, status_code: int = 200) -> Response:
    """
    Constructs a batch response structure, typically used for batch operations.
    
    :param success: Indicates whether the batch request was successful.
    :param message: A message describing the result.
    :param results: List of batch operation results.
    :param errors: Any errors to include.
    :param status_code: HTTP status code.
    :return: A Response object with the batch operation structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "batch_results": results,
        "errors": errors,
    }
    return Response(response_structure, status=status_code)


def auth_api_response(success: bool = True, message: MessageType = None, token: TokenType = None, 
                      user: UserType = None, errors: ErrorType = None, status_code: int = 200) -> Response:
    """
    Constructs an authentication response structure.
    
    :param success: Indicates whether the authentication request was successful.
    :param message: A message describing the result.
    :param token: Authentication token (e.g., JWT).
    :param user: User information.
    :param errors: Any errors to include.
    :param status_code: HTTP status code.
    :return: A Response object with the authentication structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "token": token,
        "user": user,
        "errors": errors,
    }
    return Response(response_structure, status=status_code)


def rate_limited_response(message: str = "Too many requests", retry_after: Optional[int] = None, status_code: int = 429) -> Response:
    """
    Constructs a rate-limited error response.
    
    :param message: Error message for the rate-limited response.
    :param retry_after: The time (in seconds) after which the client can retry.
    :param status_code: HTTP status code, defaults to 429.
    :return: A Response object with the rate-limited structure.
    """
    response_structure = {
        "status": "error",
        "message": message,
        "retry_after": retry_after,
    }
    return Response(response_structure, status=status_code)


def upload_progress_response(success: bool = True, message: MessageType = None, progress: Optional[int] = None, 
                             status_code: int = 200) -> Response:
    """
    Constructs an upload progress response structure.
    
    :param success: Indicates whether the upload request was successful.
    :param message: A message describing the upload progress.
    :param progress: Progress percentage (0-100).
    :param status_code: HTTP status code.
    :return: A Response object with the upload progress structure.
    """
    response_structure = {
        "status": "success" if success else "error",
        "message": message,
        "progress": progress,
    }
    return Response(response_structure, status=status_code)


def service_availability_response(available: bool = True, message: MessageType = None, service_name: Optional[str] = None, 
                                  status_code: int = 200) -> Response:
    """
    Constructs a service availability response structure.
    
    :param available: Indicates whether the service is available.
    :param message: A message describing the service status.
    :param service_name: Name of the service being checked.
    :param status_code: HTTP status code.
    :return: A Response object with the service availability structure.
    """
    response_structure = {
        "status": "available" if available else "unavailable",
        "message": message,
        "service_name": service_name,
    }
    return Response(response_structure, status=status_code)


def redirect_response(message: MessageType = None, redirect_url: Optional[str] = None, status_code: int = 302) -> Response:
    """
    Constructs a redirect response structure.
    
    :param message: A message describing the redirect.
    :param redirect_url: URL to which the client should be redirected.
    :param status_code: HTTP status code, defaults to 302 (Found).
    :return: A Response object with the redirect structure.
    """
    response_structure = {
        "status": "redirect",
        "message": message,
        "redirect_url": redirect_url,
    }
    return Response(response_structure, status=status_code)
