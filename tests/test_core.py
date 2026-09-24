from fastapi.testclient import TestClient
from app.main import app
from app.safety import classify

client = TestClient(app)

def test_health_is_mock_by_default():
    assert client.get('/health').status_code == 200

def test_high_risk_is_escalated():
    risk, intent, _ = classify('What pesticide dosage should I spray?', 'tomato')
    assert risk == 'red'
    assert intent == 'high_risk_agriculture'

def test_consent_required():
    response = client.post('/voice/query', json={'language':'hausa','audio_text':'My tomato leaves are yellow','crop':'tomato','consent':False})
    assert response.status_code == 400

def test_query_returns_trace_and_sources():
    response = client.post('/voice/query', json={'language':'hausa','audio_text':'My tomato leaves are yellow','crop':'tomato','consent':True})
    assert response.status_code == 200
    payload = response.json()
    assert payload['adapter_mode'] == 'mock'
    assert payload['source_card_ids']
    assert payload['trace']['asr_mode'] == 'mock'
    assert payload['feedback_prompt']
