# PharmaTrack Analytics (Athena)
Levanta un FastAPI que ejecuta consultas en Athena.
## Quickstart
1) Copia .env.example a .env y ajusta ATHENA_OUTPUT (s3://...).
2) Docker:
   docker compose up -d --build
3) Swagger:
   http://localhost:8080/docs
