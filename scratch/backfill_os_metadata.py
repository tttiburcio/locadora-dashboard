import sqlite3
from pathlib import Path

db_path = Path(r"c:\Users\ADM\Documents\locadora-dashboard\locadora.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("1. Filling missing IMPLEMENTO and EMPRESA from Frota...")
cursor.execute("""
    UPDATE ordens_servico
    SET implemento = (SELECT implemento FROM frota WHERE frota.id = ordens_servico.id_veiculo),
        empresa = COALESCE(empresa, (SELECT empresa FROM frota WHERE frota.id = ordens_servico.id_veiculo))
    WHERE (implemento IS NULL OR implemento = '') 
       OR (empresa IS NULL OR empresa = '');
""")
print(f"Updated implemento/empresa for {cursor.rowcount} rows.")

print("2. Backfilling FORNECEDOR from attached invoices (Notas Fiscais)...")
cursor.execute("""
    UPDATE ordens_servico
    SET fornecedor = (
        SELECT fornecedor 
        FROM notas_fiscais 
        WHERE os_id = ordens_servico.id 
          AND deletado_em IS NULL 
          AND fornecedor IS NOT NULL 
          AND fornecedor != ''
        LIMIT 1
    )
    WHERE (fornecedor IS NULL OR fornecedor = '')
      AND EXISTS (
        SELECT 1 FROM notas_fiscais 
        WHERE os_id = ordens_servico.id AND deletado_em IS NULL AND fornecedor != ''
      );
""")
print(f"Backfilled supplier name for {cursor.rowcount} rows.")

print("3. Backfilling CATEGORIA from OS items...")
cursor.execute("""
    UPDATE ordens_servico
    SET categoria = (
        SELECT categoria 
        FROM os_itens 
        WHERE os_id = ordens_servico.id 
          AND categoria IS NOT NULL 
          AND categoria != ''
        LIMIT 1
    )
    WHERE (categoria IS NULL OR categoria = '')
      AND EXISTS (
        SELECT 1 FROM os_itens 
        WHERE os_id = ordens_servico.id AND categoria != ''
      );
""")
print(f"Backfilled categories for {cursor.rowcount} rows.")

print("4. Looking up and setting FORNECEDOR_ID from master list...")
cursor.execute("""
    UPDATE ordens_servico
    SET fornecedor_id = (
        SELECT id 
        FROM fornecedores 
        WHERE UPPER(TRIM(fornecedores.nome)) = UPPER(TRIM(ordens_servico.fornecedor))
        LIMIT 1
    )
    WHERE (fornecedor_id IS NULL OR fornecedor_id = 0)
      AND fornecedor IS NOT NULL 
      AND fornecedor != '';
""")
print(f"Backfilled supplier IDs for {cursor.rowcount} rows.")

# 5. Final verification
cursor.execute("SELECT COUNT(*) FROM ordens_servico WHERE fornecedor IS NULL OR fornecedor = ''")
missing_sup = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM ordens_servico WHERE categoria IS NULL OR categoria = ''")
missing_cat = cursor.fetchone()[0]

print("\n--- SUMMARY OF OUTSTANDING ---")
print(f"Orders still missing Supplier: {missing_sup}")
print(f"Orders still missing Category: {missing_cat}")

conn.commit()
conn.close()
print("DATABASE BACKFILL COMPLETE.")
