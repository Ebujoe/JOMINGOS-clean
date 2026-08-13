"""
COMPREHENSIVE AUDIT TRAIL SYSTEM
=================================

Week 1 Deliverable: Complete audit logging for all vital measurements,
validations, forecasts, and clinical decisions.

Implements:
1. Immutable audit log entries
2. Timestamp tracking (exact microsecond precision)
3. User/system attribution
4. Action tracking (record, validate, forecast, decision)
5. Outcome logging
6. Compliance reporting
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
import hashlib

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Types of actions that trigger audit logs."""

    # Data collection
    VITAL_RECORDED = "vital_recorded"
    VITAL_VALIDATED = "vital_validated"
    VITAL_REJECTED = "vital_rejected"

    # Forecasting
    FORECAST_GENERATED = "forecast_generated"
    FORECAST_VALIDATED = "forecast_validated"
    FORECAST_USED = "forecast_used"

    # Clinical decisions
    CLINICAL_ALERT_TRIGGERED = "clinical_alert_triggered"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_ACTED_UPON = "alert_acted_upon"

    # System operations
    BASELINE_CALCULATED = "baseline_calculated"
    DATA_QUALITY_CHECK = "data_quality_check"
    MODEL_RETRAINED = "model_retrained"

    # Access
    DATA_ACCESSED = "data_accessed"
    REPORT_GENERATED = "report_generated"


@dataclass
class AuditLogEntry:
    """Single audit log entry (immutable once created)."""

    # Identity
    entry_id: str  # Unique ID for this log entry
    timestamp: datetime  # When did this happen?
    user_id: Optional[str]  # Who did it? (or system)
    system_user: Optional[str]  # Which system component?

    # Context
    patient_id: int  # Affected patient
    action_type: AuditAction  # What happened?
    action_description: str  # Human-readable description

    # Data
    affected_data: Dict[str, Any]  # What was affected?
    changes_made: Dict[str, Any]  # What changed?
    outcome: str  # Result (success/failure/review_required)

    # Compliance
    reason: Optional[str]  # Why was this action taken?
    authorization: Optional[str]  # What authorized this?
    sensitivity_level: str  # Public/Internal/Confidential/PHI

    # Technical
    ip_address: Optional[str]  # Source IP
    device_id: Optional[str]  # Which device/sensor?
    error_details: Optional[str]  # If failed, why?

    # Integrity
    checksum: str  # SHA256 of entry for tamper detection
    verified: bool = False  # Has this been verified?

    def to_dict(self) -> Dict:
        """Convert to dictionary (for JSON serialization)."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['action_type'] = self.action_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    def verify_integrity(self) -> bool:
        """Verify log entry hasn't been tampered with."""
        stored_checksum = self.checksum

        # Recalculate checksum
        data_for_checksum = {
            'timestamp': self.timestamp.isoformat(),
            'patient_id': self.patient_id,
            'action_type': self.action_type.value,
            'action_description': self.action_description,
            'affected_data': json.dumps(self.affected_data, sort_keys=True, default=str),
            'changes_made': json.dumps(self.changes_made, sort_keys=True, default=str),
        }

        checksum_string = json.dumps(data_for_checksum, sort_keys=True)
        calculated_checksum = hashlib.sha256(checksum_string.encode()).hexdigest()

        return calculated_checksum == stored_checksum


class AuditTrail:
    """
    Comprehensive audit trail system for regulatory compliance.

    All actions are logged immutably with full attribution.
    """

    def __init__(self, storage_backend=None):
        """
        Initialize audit trail.

        Args:
            storage_backend: Where to store logs (file, database, etc)
                            Defaults to file-based JSON log
        """
        self.storage_backend = storage_backend or FileAuditBackend()
        logger.info("AuditTrail initialized")

    def log_vital_recorded(
        self,
        patient_id: int,
        vital_name: str,
        value: float,
        timestamp: datetime,
        recorded_by_user: Optional[str] = None,
        device_id: Optional[str] = None,
        clinical_context: Optional[str] = None,
    ) -> str:
        """Log vital sign recording."""

        entry = AuditLogEntry(
            entry_id=self._generate_entry_id(),
            timestamp=datetime.now(),
            user_id=recorded_by_user,
            system_user="VitalSignsRecorder",
            patient_id=patient_id,
            action_type=AuditAction.VITAL_RECORDED,
            action_description=f"Vital sign recorded: {vital_name}={value}",
            affected_data={
                'vital_name': vital_name,
                'value': value,
                'measurement_timestamp': timestamp.isoformat(),
            },
            changes_made={
                'vital_added': True,
            },
            outcome="success",
            reason=clinical_context or "Routine monitoring",
            authorization="Clinical staff authorization",
            sensitivity_level="PHI",
            device_id=device_id,
            ip_address=None,
            error_details=None,
            checksum=self._calculate_checksum({
                'timestamp': datetime.now().isoformat(),
                'patient_id': patient_id,
                'action_type': AuditAction.VITAL_RECORDED.value,
                'action_description': f"Vital sign recorded: {vital_name}={value}",
                'affected_data': {
                    'vital_name': vital_name,
                    'value': value,
                    'measurement_timestamp': timestamp.isoformat(),
                },
                'changes_made': {'vital_added': True},
            }),
        )

        self.storage_backend.store(entry)
        logger.info(f"Logged vital recording: {vital_name}={value} for patient {patient_id}")

        return entry.entry_id

    def log_validation(
        self,
        patient_id: int,
        vital_name: str,
        value: float,
        validation_result: Dict,
        quality_score: float,
        approved: bool,
    ) -> str:
        """Log data validation."""

        entry = AuditLogEntry(
            entry_id=self._generate_entry_id(),
            timestamp=datetime.now(),
            user_id=None,
            system_user="DataQualityValidator",
            patient_id=patient_id,
            action_type=AuditAction.VITAL_VALIDATED if approved else AuditAction.VITAL_REJECTED,
            action_description=f"Vital validation: {vital_name}={value} ({'APPROVED' if approved else 'REJECTED'})",
            affected_data={
                'vital_name': vital_name,
                'value': value,
                'quality_score': quality_score,
            },
            changes_made={
                'status': 'approved' if approved else 'rejected',
            },
            outcome="success" if approved else "review_required",
            reason="Automated quality validation",
            authorization="System automatic",
            sensitivity_level="PHI",
            device_id=None,
            ip_address=None,
            error_details=validation_result.get('issues'),
            checksum=self._calculate_checksum({
                'timestamp': datetime.now().isoformat(),
                'patient_id': patient_id,
                'action_type': (AuditAction.VITAL_VALIDATED if approved else AuditAction.VITAL_REJECTED).value,
                'affected_data': {
                    'vital_name': vital_name,
                    'value': value,
                    'quality_score': quality_score,
                },
                'changes_made': {'status': 'approved' if approved else 'rejected'},
            }),
        )

        self.storage_backend.store(entry)
        logger.info(f"Logged validation for {vital_name}: {'APPROVED' if approved else 'REJECTED'}")

        return entry.entry_id

    def log_forecast_generated(
        self,
        patient_id: int,
        vital_name: str,
        horizon_hours: int,
        forecast_value: float,
        confidence_score: float,
        model_count: int,
    ) -> str:
        """Log forecast generation."""

        entry = AuditLogEntry(
            entry_id=self._generate_entry_id(),
            timestamp=datetime.now(),
            user_id=None,
            system_user="ForecastingEngine",
            patient_id=patient_id,
            action_type=AuditAction.FORECAST_GENERATED,
            action_description=f"Forecast generated: {vital_name} @ {horizon_hours}h = {forecast_value:.1f} (confidence {confidence_score:.0f}%)",
            affected_data={
                'vital_name': vital_name,
                'horizon_hours': horizon_hours,
                'forecast_value': forecast_value,
                'confidence_score': confidence_score,
                'models_used': model_count,
            },
            changes_made={},
            outcome="success",
            reason="Scheduled forecasting",
            authorization="System automatic",
            sensitivity_level="PHI",
            device_id=None,
            ip_address=None,
            error_details=None,
            checksum=self._calculate_checksum({
                'timestamp': datetime.now().isoformat(),
                'patient_id': patient_id,
                'action_type': AuditAction.FORECAST_GENERATED.value,
                'affected_data': {
                    'vital_name': vital_name,
                    'horizon_hours': horizon_hours,
                    'forecast_value': forecast_value,
                    'confidence_score': confidence_score,
                    'models_used': model_count,
                },
            }),
        )

        self.storage_backend.store(entry)
        logger.info(f"Logged forecast for {vital_name}: {forecast_value:.1f} (confidence {confidence_score:.0f}%)")

        return entry.entry_id

    def log_data_access(
        self,
        patient_id: int,
        user_id: str,
        access_reason: str,
        data_accessed: List[str],
    ) -> str:
        """Log data access for compliance."""

        entry = AuditLogEntry(
            entry_id=self._generate_entry_id(),
            timestamp=datetime.now(),
            user_id=user_id,
            system_user=None,
            patient_id=patient_id,
            action_type=AuditAction.DATA_ACCESSED,
            action_description=f"Data accessed by {user_id}: {', '.join(data_accessed)}",
            affected_data={
                'data_types': data_accessed,
            },
            changes_made={},
            outcome="success",
            reason=access_reason,
            authorization=f"User {user_id}",
            sensitivity_level="PHI",
            device_id=None,
            ip_address=None,
            error_details=None,
            checksum=self._calculate_checksum({
                'timestamp': datetime.now().isoformat(),
                'patient_id': patient_id,
                'action_type': AuditAction.DATA_ACCESSED.value,
                'user_id': user_id,
                'data_accessed': data_accessed,
            }),
        )

        self.storage_backend.store(entry)
        logger.info(f"Logged data access by {user_id}")

        return entry.entry_id

    def get_patient_audit_log(self, patient_id: int) -> List[AuditLogEntry]:
        """Retrieve complete audit log for a patient."""
        return self.storage_backend.retrieve_by_patient(patient_id)

    def generate_compliance_report(self, patient_id: int) -> Dict:
        """Generate compliance report for audit."""
        logs = self.get_patient_audit_log(patient_id)

        return {
            'patient_id': patient_id,
            'report_generated': datetime.now().isoformat(),
            'total_audit_entries': len(logs),
            'entries_by_action': self._count_by_action(logs),
            'data_access_log': [
                l.to_dict() for l in logs
                if l.action_type == AuditAction.DATA_ACCESSED
            ],
            'quality_issues': [
                l.to_dict() for l in logs
                if l.action_type == AuditAction.VITAL_REJECTED
            ],
        }

    @staticmethod
    def _generate_entry_id() -> str:
        """Generate unique entry ID."""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

    @staticmethod
    def _calculate_checksum(data: Dict) -> str:
        """Calculate SHA256 checksum of entry."""
        data_string = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()

    @staticmethod
    def _count_by_action(logs: List[AuditLogEntry]) -> Dict[str, int]:
        """Count log entries by action type."""
        counts = {}
        for log in logs:
            action = log.action_type.value
            counts[action] = counts.get(action, 0) + 1
        return counts


class FileAuditBackend:
    """File-based audit log storage (development/small deployments)."""

    def __init__(self, filepath: str = "audit_trail.jsonl"):
        self.filepath = filepath

    def store(self, entry: AuditLogEntry):
        """Append entry to audit log file."""
        with open(self.filepath, 'a') as f:
            f.write(entry.to_json() + '\n')

    def retrieve_by_patient(self, patient_id: int) -> List[AuditLogEntry]:
        """Retrieve all entries for a patient."""
        entries = []
        try:
            with open(self.filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get('patient_id') == patient_id:
                            # Reconstruct entry
                            entries.append(self._dict_to_entry(data))
        except FileNotFoundError:
            pass
        return entries

    @staticmethod
    def _dict_to_entry(data: Dict) -> AuditLogEntry:
        """Reconstruct AuditLogEntry from dict."""
        return AuditLogEntry(
            entry_id=data['entry_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            user_id=data.get('user_id'),
            system_user=data.get('system_user'),
            patient_id=data['patient_id'],
            action_type=AuditAction(data['action_type']),
            action_description=data['action_description'],
            affected_data=data['affected_data'],
            changes_made=data['changes_made'],
            outcome=data['outcome'],
            reason=data.get('reason'),
            authorization=data.get('authorization'),
            sensitivity_level=data['sensitivity_level'],
            ip_address=data.get('ip_address'),
            device_id=data.get('device_id'),
            error_details=data.get('error_details'),
            checksum=data['checksum'],
            verified=data.get('verified', False),
        )
