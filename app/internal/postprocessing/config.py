from typing import Literal, Optional

from sqlmodel import Session

from app.util.cache import StringConfigCache


class DownclientMisconfigured(ValueError):
    pass


PostProcessingKey = Literal[
    "postprocessing_auto_moving",
    "postprocessing_disable_hardlinking",
]


class PostProcessingConfig(StringConfigCache[PostProcessingKey]):
    def is_valid(self, session: Session) -> bool:
        return (
            self.get_auto_moving(session) is not None
        )

    def raise_if_invalid(self, session: Session):
        if not self.get_auto_moving(session):
            raise DownclientMisconfigured("Post Processing active not set")

    def get_auto_moving(self, session: Session) -> Optional[bool]:
        return self.get_bool(session, "postprocessing_auto_moving")

    def set_auto_moving(self, session: Session, active: bool):
        self.set_bool(session, "postprocessing_auto_moving", active)

    def get_disable_hardlinking(self, session: Session) -> Optional[bool]:
        return self.get_bool(session, "postprocessing_disable_hardlinking")

    def set_disable_hardlinking(self, session: Session, active: bool):
        self.set_bool(session, "postprocessing_disable_hardlinking", active)

postprocessing_config = PostProcessingConfig()
