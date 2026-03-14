import os
from pydantic import BaseModel


class FolderAvailability(BaseModel):
    path: str
    accessible: bool

def path_accessible(path: str) -> bool:
    return (
        os.access(path, os.F_OK)
        and os.access(path, os.R_OK)
        and os.access(path, os.W_OK)
    )
