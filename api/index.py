"""A small WSGI API reusing the original Python logic, without Streamlit state.

Run locally: python -m flask --app api.index run --host 0.0.0.0 --port 8000
No assessment inputs or history are written to server disk or a cloud database.
"""
import json
import logging
from functools import lru_cache
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from src.config import ROOT, FIELDS, CATEGORY_FIELDS, CATEGORY_WEIGHTS, SECTION_HELP, BANDS, SCORING_VERSION
from src.readiness_scoring import assess, validate_inputs, ValidationError
from src.recommendations import recommend, seven_day_plan

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024


@app.after_request
def safe_response(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('Send a JSON object containing assessment inputs.')
    return data


@app.errorhandler(ValidationError)
@app.errorhandler(ValueError)
def invalid(exc):
    return jsonify(error=str(exc)), 422


@app.errorhandler(RequestEntityTooLarge)
def too_large(exc):
    return jsonify(error='This request is too large. Submit one assessment at a time.'), 413


@app.errorhandler(BadRequest)
def bad_json(exc):
    return jsonify(error='Please send valid JSON.'), 400


@app.get('/api/health')
def health():
    return jsonify(status='ok', scoring_version=SCORING_VERSION, history='browser-only')


@app.get('/api/config')
def config():
    return jsonify(
        fields={k: dict(label=v[0], minimum=v[1], maximum=v[2], default=v[3], optional=v[4], cap=v[5], integer=isinstance(v[1], int)) for k, v in FIELDS.items()},
        categories=[dict(name=cat, weight=weight, fields=CATEGORY_FIELDS[cat], help=SECTION_HELP[cat]) for cat, weight in CATEGORY_WEIGHTS.items()],
        bands=BANDS, scoring_version=SCORING_VERSION,
    )


@app.post('/api/validate')
def validate():
    body = payload()
    category = body.get('category')
    if category not in CATEGORY_FIELDS:
        raise ValidationError('Choose a valid assessment section.')
    inputs = body.get('inputs')
    if not isinstance(inputs, dict):
        raise ValidationError('Assessment inputs must be an object.')
    return jsonify(inputs=validate_inputs(inputs, fields=CATEGORY_FIELDS[category]))


@app.post('/api/assess')
def assessment():
    inputs = payload()
    result = assess(inputs)
    return jsonify(**result, recommendations=recommend(result['inputs']), plan=seven_day_plan(result['inputs']))


@app.get('/api/model')
def model_insights():
    try:
        meta = json.loads((ROOT / 'models/model_metadata.json').read_text())
        if meta.get('synthetic') is not True:
            raise ValueError('Synthetic declaration required')
        return jsonify(meta)
    except (OSError, ValueError):
        return jsonify(error='Model insights are unavailable. Regenerate the model artifacts. Readiness scoring still works.'), 503


@lru_cache(maxsize=1)
def model_pipeline():
    from src.predict import load_model
    return load_model()[0]


@app.post('/api/simulate')
def simulate():
    # ML dependencies are imported lazily: everyday scoring remains lightweight.
    import pandas as pd
    from src.predict import predict_simulated, ModelError
    body = payload()
    try:
        predicted = predict_simulated(pd.DataFrame([body]), model_pipeline())
        return jsonify(simulated_class=int(predicted[0]), synthetic=True,
                       explanation='Simulated exercise class only. Not a placement prediction or hiring probability.')
    except ModelError:
        return jsonify(error='The saved educational model is unavailable. Readiness assessments still work.'), 503
    except (TypeError, KeyError):
        return jsonify(error='Use the documented seven-feature simulation schema.'), 422


@app.errorhandler(404)
def missing(exc):
    return jsonify(error='This API endpoint does not exist.'), 404


@app.errorhandler(500)
def unexpected(exc):
    # No request body or personal assessment data is logged here.
    logging.error('Path2Placement API request failed')
    return jsonify(error='Something went wrong. Please try again; your browser draft is still available.'), 500
