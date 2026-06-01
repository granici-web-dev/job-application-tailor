"""Exceptions that carry a message meant to be shown directly to the user."""


class TailorError(Exception):
    pass


class ConfigError(TailorError):
    pass


class JobFetchError(TailorError):
    pass


class JobAnalysisError(TailorError):
    pass


class ProfileError(TailorError):
    pass


class TrackerError(TailorError):
    pass


class ApplicationNotFoundError(TailorError):
    pass
