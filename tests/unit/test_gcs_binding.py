"""Unit tests for GCS tenant binding helpers."""
import pytest

from auth_broker.gcs import assert_gcs_uri_owned_by_patient


def test_assert_gcs_uri_owned_by_patient_accepts_matching_path():
    assert_gcs_uri_owned_by_patient(
        "gs://bucket/prescriptions/patient-abc/photo.jpg",
        "patient-abc",
    )


def test_assert_gcs_uri_owned_by_patient_rejects_wrong_patient():
    with pytest.raises(ValueError, match="does not belong"):
        assert_gcs_uri_owned_by_patient(
            "gs://bucket/prescriptions/patient-a/photo.jpg",
            "patient-b",
        )


def test_assert_gcs_uri_owned_by_patient_rejects_non_prescriptions_prefix():
    with pytest.raises(ValueError, match="prescriptions"):
        assert_gcs_uri_owned_by_patient(
            "gs://bucket/eval/smoke.png",
            "patient-a",
        )


def test_assert_gcs_uri_owned_by_patient_rejects_legacy_uuid_only_path():
    with pytest.raises(ValueError, match="prescriptions"):
        assert_gcs_uri_owned_by_patient(
            "gs://bucket/prescriptions/abc123.jpg",
            "patient-a",
        )
