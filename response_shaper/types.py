from typing import Dict, List, Union, Optional, NewType

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
