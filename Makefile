
.PHONY: test
lint:
	isort event_sourcery/ event_sourcery_sqlalchemy/ event_sourcery_kombu/ event_sourcery_esdb/ event_sourcery_django/ tests/
	black event_sourcery/ event_sourcery_sqlalchemy/ event_sourcery_kombu/ event_sourcery_esdb/ event_sourcery_django/ tests/
	mypy event_sourcery/ event_sourcery_sqlalchemy/ event_sourcery_kombu/ event_sourcery_esdb/ event_sourcery_django/ tests/
	flake8 event_sourcery/ event_sourcery_sqlalchemy/ event_sourcery_kombu/ event_sourcery_esdb/ event_sourcery_django/ tests/

.PHONY: test
test:
	pytest --cov event_sourcery --cov event_sourcery_sqlalchemy --cov event_sourcery_kombu/ --cov event_sourcery_esdb/ --cov event_sourcery_django/ tests/

