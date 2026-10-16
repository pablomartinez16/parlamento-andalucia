#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: El archivo ${BACKUP_FILE} no existe."
    exit 1
fi

echo "⚠️ ATENCIÓN: Esta operación sobreescribirá los datos actuales en la base de datos."
read -p "¿Deseas continuar? (s/N): " confirm
if [[ ! "$confirm" =~ ^[sS]$ ]]; then
    echo "Operación cancelada."
    exit 0
fi

echo "[$(date)] Restaurando base de datos desde ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD:-parlamento_pass}" psql -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-parlamento_user}" -d "${POSTGRES_DB:-parlamento_db}"

echo "[$(date)] Restauración completada con éxito."
