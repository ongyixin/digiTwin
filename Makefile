.PHONY: eval eval-extraction eval-citations eval-permissions

## Run the full evaluation harness
eval: eval-extraction eval-citations eval-permissions

## Run extraction accuracy tests only
eval-extraction:
	cd backend && PYTHONPATH=. pytest tests/eval/extraction_accuracy.py -v

## Run citation faithfulness tests only
eval-citations:
	cd backend && PYTHONPATH=. pytest tests/eval/citation_faithfulness.py -v

## Run permission correctness tests only
eval-permissions:
	cd backend && PYTHONPATH=. pytest tests/eval/permission_correctness.py -v

## Run all backend tests
test:
	cd backend && PYTHONPATH=. pytest tests/ -v

## Start development servers
dev:
	docker-compose up --build

## Start backend only
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

## Start frontend only
dev-frontend:
	cd frontend && npm run dev
