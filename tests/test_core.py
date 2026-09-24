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

def test_farm_log_and_metrics_endpoints():
    response = client.post('/farm-log', json={'language':'hausa','activity_text':'Today I planted maize','crop':'maize','consent':True})
    assert response.status_code == 200
    assert response.json()['activity'] == 'planting'
    history = client.get('/history')
    assert history.status_code == 200
    metrics = client.get('/metrics')
    assert metrics.status_code == 200
    assert 'total_interactions' in metrics.json()

def test_natlas_evidence_page_is_honest_about_mock_mode():
    response = client.get('/natlas')
    assert response.status_code == 200
    assert 'MOCK MODE' in response.text

def test_record_level_evidence_lookup():
    response = client.post('/voice/query', json={'language':'yoruba','audio_text':'My maize leaves are yellow','crop':'maize','consent':True})
    interaction_id = response.json()['interaction_id']
    evidence = client.get(f'/evidence/{interaction_id}')
    assert evidence.status_code == 200
    assert evidence.json()['trace']['asr_mode'] == 'mock'
