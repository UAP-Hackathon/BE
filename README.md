## Skill Bridge
## Setup

0. setup

```bash

python3 -m venv venv
source ./venv/bin/activate

pip3 install -r requirements.txt
```

1. run docker
```python
docker-compose up --build
```
2. run migration and start server
```bash
alembic upgrade head && uvicorn main:app --reload
```


