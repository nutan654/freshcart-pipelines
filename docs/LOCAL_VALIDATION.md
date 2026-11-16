# Local Validation Environment

The project automated tests are configured to run through GitHub Actions.

## Local Setup
1. Install Python 3.12.
2. Install dependencies using python -m pip install -r requirements.txt.
3. Install pytest using python -m pip install pytest.
4. Run tests using python -m pytest -q.

## External Services
Snowflake and RabbitMQ tests require their respective services and credentials.
Mage pipeline execution requires a configured Mage environment.
