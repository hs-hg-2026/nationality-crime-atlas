"""Project-specific exceptions."""


class SchemaError(ValueError):
    """Raised when an official source no longer matches the expected schema."""


class IntegrityError(ValueError):
    """Raised when an artifact fails an expected integrity property."""


class SnapshotConflictError(IntegrityError):
    """Raised when an immutable snapshot location already has different content."""


class PipelineConflictError(IntegrityError):
    """Raised when an existing processed run fails idempotence verification."""


class QualityGateError(ValueError):
    """Raised when normalized output fails its source quality profile."""

    def __init__(self, report):
        self.report = report
        super().__init__(
            "Quality gate failed with %d errors" % report.get("error_count", 0)
        )


class AcquisitionError(RuntimeError):
    """Raised when an official artifact cannot be acquired safely."""


class MappingConflictError(IntegrityError):
    """Raised when a timestamped mapping run would overwrite prior output."""
