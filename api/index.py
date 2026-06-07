from mangum import Mangum
from app.main import app

# Vercel serverless entry point — wraps the FastAPI ASGI app as a Lambda handler.
# lifespan="off" skips startup/shutdown events that don't apply in serverless.
handler = Mangum(app, lifespan="off")
