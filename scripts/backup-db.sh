#!/usr/bin/env bash
set -euo pipefail
umask 077
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT"
: "${ORBE_BACKUP_DIR:?Defina ORBE_BACKUP_DIR para diretório FORA do repositório}"
if [[ "$ORBE_BACKUP_DIR" == "$PROJECT"* ]]; then
  echo "Backup deve ficar fora do checkout Git" >&2
  exit 2
fi
mkdir -p "$ORBE_BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$ORBE_BACKUP_DIR/orbe-$STAMP.dump"
TMP="$TARGET.part"
trap 'rm -f "$TMP"' EXIT
docker compose exec -T db pg_dump -U orbe -d orbe -Fc > "$TMP"
docker compose exec -T db pg_restore -l < "$TMP" >/dev/null
test -s "$TMP"
mv "$TMP" "$TARGET"
trap - EXIT
sha256sum "$TARGET" > "$TARGET.sha256"
echo "Backup validado: $TARGET"
