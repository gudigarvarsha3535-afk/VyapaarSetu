import pytest
import base64
import wave
import io
from backend.services.audio_service import audio_service, AudioConversionError
from backend.database import db

def create_synthetic_wav(duration_seconds=1.0, sample_rate=16000) -> bytes:
    """Generates synthetic 16kHz mono WAV bytes in memory."""
    buf = io.BytesIO()
    num_frames = int(duration_seconds * sample_rate)
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Write dummy silence/sine
        wf.writeframes(b'\x00\x00' * num_frames)
    return buf.getvalue()

def test_decode_base64_audio():
    sample = b"hello audio"
    b64_raw = base64.b64encode(sample).decode("utf-8")
    assert audio_service.decode_base64_audio(b64_raw) == sample

    # With data URL prefix
    data_url = f"data:audio/webm;base64,{b64_raw}"
    assert audio_service.decode_base64_audio(data_url) == sample

def test_decode_corrupt_base64():
    with pytest.raises(AudioConversionError):
        audio_service.decode_base64_audio("not_valid_base64!!!")

def test_decode_empty_base64():
    with pytest.raises(AudioConversionError):
        audio_service.decode_base64_audio("   ")

def test_audio_duration_and_energy():
    # 1.0s synthetic audio -> not noise
    wav_1s = create_synthetic_wav(duration_seconds=1.0)
    dur, is_noise = audio_service.check_audio_duration_and_energy(wav_1s)
    assert 0.9 <= dur <= 1.1
    assert is_noise is False

    # 0.1s synthetic audio -> classified as click noise/too short
    wav_short = create_synthetic_wav(duration_seconds=0.1)
    dur_short, is_noise_short = audio_service.check_audio_duration_and_energy(wav_short)
    assert is_noise_short is True

def test_product_catalog_kannada_alias_matching():
    db.reset()

    # "akki" -> Sona Masoori Rice (Akki)
    prod_akki = db.find_product_by_name("akki")
    assert prod_akki is not None
    assert "prod_102" == prod_akki.id

    # "tuppa" / "ghee" -> Nandini Pure Ghee
    prod_tuppa = db.find_product_by_name("tuppa")
    assert prod_tuppa is not None
    assert "prod_101" == prod_tuppa.id

    # "bellulli" -> Fresh Garlic (Bellulli)
    prod_bellulli = db.find_product_by_name("bellulli")
    assert prod_bellulli is not None
    assert "prod_106" == prod_bellulli.id

    # "menasinakayi" -> Byadgi Chilli Powder
    prod_chilli = db.find_product_by_name("menasinakayi")
    assert prod_chilli is not None
    assert "prod_104" == prod_chilli.id

    # "sabun" -> Mysore Sandal Soap
    prod_soap = db.find_product_by_name("sabun")
    assert prod_soap is not None
    assert "prod_103" == prod_soap.id

    # Non-existent product returns None safely
    assert db.find_product_by_name("non_existent_item_xyz") is None
