#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT"
FILE="${1:?Informe o arquivo .dump produzido por backup-db.sh}"
test -s "$FILE" || { echo "Backup inexistente ou vazio" >&2; exit 2; }
if [[ -f "$FILE.sha256" ]]; then
  (cd "$(dirname "$FILE")" && sha256sum -c "$(basename "$FILE").sha256")
fi
TEMP_DB="orbe_check_$(date -u +%s)_$RANDOM"
cleanup() {
  docker compose exec -T db dropdb -U orbe --if-exists "$TEMP_DB" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker compose exec -T db createdb -U orbe "$TEMP_DB"
docker compose exec -T db pg_restore -U orbe -d "$TEMP_DB" --no-owner --no-privileges < "$FILE"
COUNT="$(docker compose exec -T db psql -U orbe -d "$TEMP_DB" -v ON_ERROR_STOP=1 -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('usuarios','protocolos','compras','contratos');")"
test "$COUNT" = "4" || { echo "Restauração incompleta (tabelas=$COUNT)" >&2; exit 3; }
echo "Restauração temporária OK: 4 tabelas essenciais verificadas"
