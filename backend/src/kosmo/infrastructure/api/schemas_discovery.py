from pydantic import BaseModel


class DiscoveryDocumentRequest(BaseModel):
    document: str


class DiscoveryDocumentResponse(BaseModel):
    document: str
