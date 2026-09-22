"""
Refuerzo a nivel de base de datos de la inmutabilidad de AuditLog.

El ORM ya bloquea UPDATE/DELETE (ver AuditLog.save/delete y AuditLogQuerySet),
pero cualquier acceso directo por SQL o un borrado en cascada podría saltárselo.
Estos triggers de PostgreSQL garantizan que la tabla sea estrictamente append-only.
"""
from django.db import migrations

TABLE = "documents_auditlog"
FUNCTION = "brevetto_prevent_auditlog_mutation"

FORWARD_SQL = f"""
CREATE OR REPLACE FUNCTION {FUNCTION}() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'AuditLog es append-only: operacion % no permitida sobre {TABLE}', TG_OP
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auditlog_prevent_update ON {TABLE};
CREATE TRIGGER auditlog_prevent_update
    BEFORE UPDATE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION {FUNCTION}();

DROP TRIGGER IF EXISTS auditlog_prevent_delete ON {TABLE};
CREATE TRIGGER auditlog_prevent_delete
    BEFORE DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION {FUNCTION}();
"""

BACKWARD_SQL = f"""
DROP TRIGGER IF EXISTS auditlog_prevent_update ON {TABLE};
DROP TRIGGER IF EXISTS auditlog_prevent_delete ON {TABLE};
DROP FUNCTION IF EXISTS {FUNCTION}();
"""


def install_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        # El stack oficial es PostgreSQL 16; en otros motores solo aplica la guarda del ORM.
        return
    # params=None evita que psycopg interprete el '%' de RAISE EXCEPTION como placeholder.
    schema_editor.execute(FORWARD_SQL, params=None)


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(BACKWARD_SQL, params=None)


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(install_triggers, remove_triggers),
    ]
