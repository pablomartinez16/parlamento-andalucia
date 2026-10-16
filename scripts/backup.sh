#!/bin/bash
set -euo pipefail

# Configuración
BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/parlamento_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Iniciando copia de seguridad de PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD:-parlamento_pass}" pg_dump -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-parlamento_user}" -d "${POSTGRES_DB:-parlamento_db}" | gzip > "${BACKUP_FILE}"

echo "[$(date)] Backup completado con éxito: ${BACKUP_FILE}"

# Rotación automática de backups antiguos
echo "[$(date)] Eliminando copias con más de ${RETENTION_DAYS} días..."
find "${BACKUP_DIR}" -name "parlamento_db_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Proceso de copia y rotación finalizado."
