from typing import Callable, Dict, List, NewType, Optional, Union

from rest_framework.response import Response

# Custom Types
StatusType = Union[str, bool]
MessageType = Optional[str]
DataType = Optional[Union[Dict, List]]
ErrorType = Optional[Union[Dict, List]]
LinksType = Optional[Dict[str, str]]
PageNumber = Union[int, None]
TotalPages = Union[int, None]
TotalItems = Union[int, None]
TokenType = Optional[str]
UserType = Optional[Dict[str, Union[str, int]]]
Timestamp = NewType("Timestamp", str)
ProcessingTime = Optional[str]
ResultsType = Optional[List[Dict[str, Union[str, int, Dict]]]]

# Define a generic response function type
ResponseFuncType = Callable[..., Response]
