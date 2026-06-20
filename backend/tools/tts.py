"""
backend/tools/tts.py
FunctionTool: GCP Text-to-Speech → GCS MP3 signed URL.

In local mode (ENVIRONMENT=local), returns a stub URL immediately.
In production, calls GCP TTS, uploads the MP3 to GCS, and returns a 24h signed URL.
"""
import logging
import os

from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

_STUB_AUDIO_URL = "https://stub.local/audio/stub.mp3"

_VOICE_MAP = {
    "hi-IN": "hi-IN-Standard-A",
    "ta-IN": "ta-IN-Standard-A",
    "te-IN": "te-IN-Standard-A",
    "bn-IN": "bn-IN-Standard-A",
    "en-IN": "en-IN-Standard-A",
}


def _signed_get_url(blob) -> str:
    """Return a V4 signed GET URL.

    Agent Runtime uses metadata credentials (no private key). Pass access_token
    so the storage client can sign via IAM signBlob instead of a local key.
    """
    import datetime

    import google.auth
    from google.auth.transport import requests as auth_requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_request = auth_requests.Request()
    credentials.refresh(auth_request)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=24),
        method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


def text_to_speech(text: str, language_code: str) -> dict:
    """Synthesize speech from text and return a GCS signed URL.

    Args:
        text: The text to synthesize (max ~4 900 characters).
        language_code: BCP-47 tag. One of: hi-IN, ta-IN, te-IN, bn-IN, en-IN.

    Returns:
        {"audio_url": str, "duration_seconds": int}
    """
    if os.getenv("ENVIRONMENT") == "local":
        logger.info("TTS stub: language=%s len=%d", language_code, len(text))
        return {"audio_url": _STUB_AUDIO_URL, "duration_seconds": 0}

    import datetime

    from google.cloud import storage, texttospeech

    tts_client = texttospeech.TextToSpeechClient()

    voice_name = _VOICE_MAP.get(language_code, "en-IN-Standard-A")
    response = tts_client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text[:4900]),
        voice=texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        ),
    )

    bucket_name = os.getenv("GCS_BUCKET", "medication-companion-uploads")
    blob_name = f"audio/{language_code}/{os.urandom(8).hex()}.mp3"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(response.audio_content, content_type="audio/mpeg")

    signed_url = _signed_get_url(blob)

    # MP3 at ~24 kbps ≈ 3 000 bytes/s
    duration_seconds = max(1, len(response.audio_content) // 3000)

    return {"audio_url": signed_url, "duration_seconds": duration_seconds}


tts_tool = FunctionTool(text_to_speech)
