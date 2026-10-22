import pytest
from api.index import app
from src.readiness_scoring import assess
from src.recommendations import recommend, seven_day_plan


@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()


def test_config_health(client):
    assert client.get('/api/health').json['history'] == 'browser-or-account'
    config = client.get('/api/config').json
    assert len(config['fields']) == 20
    assert len(config['categories']) == 5
    assert sum(c['weight'] for c in config['categories']) == pytest.approx(1)
    assert client.get('/api/config').headers['Cache-Control'] == 'no-store'


def test_api_reuses_original_scoring(client, inputs):
    response = client.post('/api/assess', json=inputs)
    assert response.status_code == 200
    original = assess(inputs)
    for key in original:
        assert response.json[key] == original[key]
    assert response.json['recommendations'] == recommend(inputs)
    assert response.json['plan'] == seven_day_plan(inputs)
    assert 'Set-Cookie' not in response.headers


def test_section_validation(client, inputs):
    response = client.post('/api/validate', json={'category':'Academic preparation', 'inputs':{k:inputs[k] for k in ('cgpa','core','consistency')}})
    assert response.status_code == 200
    inputs.update(projects=0, demos=2)
    response = client.post('/api/validate', json={'category':'Projects & experience','inputs':inputs})
    assert response.status_code == 422
    assert 'cannot exceed' in response.json['error']


@pytest.mark.parametrize('body', [[], None, {'cgpa':-1}, {'cgpa':'8'}, {'cgpa':True}])
def test_invalid_requests(client, body):
    response = client.post('/api/assess', json=body)
    assert response.status_code == 422
    assert 'error' in response.json


def test_invalid_category(client):
    assert client.post('/api/validate', json={'category':'unknown','inputs':{}}).status_code == 422
    assert client.post('/api/validate', json={'category':'Academic preparation','inputs':[]}).status_code == 422


def test_bad_json_and_body_limits(client):
    assert client.post('/api/assess', data='{invalid', content_type='application/json').status_code == 422
    assert client.post('/api/assess', json={'large':'x'*40000}).status_code == 413
    assert client.get('/api/no-such-endpoint').status_code == 404


def test_optional_missing_and_boundaries(client):
    from src.config import FIELDS
    weak = {k:v[1] for k,v in FIELDS.items()}
    strong = {k:v[2] for k,v in FIELDS.items()}
    assert client.post('/api/assess', json=weak).json['score'] == 0
    assert client.post('/api/assess', json=strong).json['score'] == 100
    strong['mock'] = None
    assert client.post('/api/assess', json=strong).json['score'] == 100


def test_actual_saved_pipeline_inference(client):
    from src.data_preprocessing import generate_synthetic, FEATURES
    frame = generate_synthetic(10)[FEATURES].iloc[0].fillna(50).to_dict()
    response = client.post('/api/simulate', json=frame)
    assert response.status_code == 200
    assert response.json['simulated_class'] in (0, 1)
    assert response.json['synthetic'] is True
    assert 'placement prediction' in response.json['explanation']
    assert client.post('/api/simulate', json={**frame,'future_salary':100}).status_code == 422


def test_model_metadata_is_real(client):
    response = client.get('/api/model')
    assert response.status_code == 200
    assert response.json['synthetic'] is True
    assert response.json['test_rows'] == 280
    assert len(response.json['comparison']) == 3


@pytest.mark.parametrize('category', [[], {}, 3, None])
def test_invalid_category_types_are_helpful(client, category):
    assert client.post('/api/validate', json={'category':category,'inputs':{}}).status_code == 422


def test_model_failure_does_not_break_readiness(client, inputs, monkeypatch):
    from api import index
    from src.predict import ModelError
    def unavailable():
        raise ModelError('unavailable')
    monkeypatch.setattr(index, 'model_pipeline', unavailable)
    body={'cgpa':7,'coding_practice':80,'dsa_rating':3,'project_quality':3,'aptitude':60,'communication':3,'internship':'none'}
    assert client.post('/api/simulate', json=body).status_code == 503
    assert client.post('/api/assess', json=inputs).status_code == 200
