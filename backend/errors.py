"""Exceptions that carry a message meant to be shown directly to the user."""


class TailorError(Exception):
    pass


class ConfigError(TailorError):
    pass


class JobFetchError(TailorError):
    pass


class JobAnalysisError(TailorError):
    pass


class LLMError(TailorError):
    pass


class ProfileError(TailorError):
    pass


class TrackerError(TailorError):
    pass


class ApplicationNotFoundError(TailorError):
    pass


class FactCheckError(TailorError):
    pass


class JobTitleMissingError(TailorError):
    """The posting names no position; the pipeline waits for one entered by hand."""

    def __init__(self) -> None:
        super().__init__("Название позиции не найдено, укажите его вручную")
