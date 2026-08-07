import logging
from dataclasses import dataclass, field

from typing_extensions import Self


@dataclass
class LoggerContext:
    action: str
    level: int = logging.DEBUG
    swallow_exceptions: bool = False
    extra: dict[str, str] = field(default_factory=dict)
    logger: logging.Logger | None = None

    def set_extra(self, key: str, value: str) -> None:
        self.extra[key] = value

    def __enter__(self) -> Self:
        if not self.logger:
            self.logger = logging.getLogger(__name__)
        return self

    def __exit__(self, exctype, value, tb) -> bool:  # noqa: ANN001
        if exctype is None:
            self.logger.log(self.level, self.action, extra=self.extra)
            return True

        self.logger.log(
                self.level, f"failed {self.action}. {exctype.__name__}: {value}", extra=self.extra
        )
        return self.swallow_exceptions
