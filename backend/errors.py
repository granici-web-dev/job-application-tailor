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


class ContactDetailsMissingError(TailorError):
    """The posting names no contact person or no address; the page offers both fields."""

    def __init__(self, *, contact_person: str | None, address: str | None) -> None:
        super().__init__("В вакансии нет контактного лица или адреса. Укажите их, если знаете; оба поля необязательны")
        self.contact_person = contact_person
        self.address = address


class JobTextMissingError(TailorError):
    """The posting is rendered with JavaScript; the pipeline waits for its text pasted by hand."""

    def __init__(self) -> None:
        super().__init__("Вакансия загружается через JavaScript, вставьте текст вакансии вручную")
