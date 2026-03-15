import sqlite3
import os
import shutil
import json
import uuid
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from utilidades import converter_data_seguro

# --- SISTEMA "STEALTH" (MEMÓRIA INVISÍVEL) ---
if os.name == 'nt':
    PASTA_OCULTA_SISTEMA = os.path.join(os.getenv('APPDATA'), "SistemaCaixa_Sys")
else:
    PASTA_OCULTA_SISTEMA = os.path.join(os.path.expanduser("~"), ".sistemacaixa_sys")

if not os.path.exists(PASTA_OCULTA_SISTEMA):
    try:
        os.makedirs(PASTA_OCULTA_SISTEMA)
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(PASTA_OCULTA_SISTEMA, 2) 
    except:
        pass 

ARQUIVO_MEMORIA = os.path.join(PASTA_OCULTA_SISTEMA, "config.json")

def conectar_caminho_dados():
    caminho_dados = None
    if os.path.exists(ARQUIVO_MEMORIA):
        try:
            with open(ARQUIVO_MEMORIA, 'r') as f:
                dados = json.load(f)
                teste = dados.get('local_banco')
                if teste and os.path.exists(teste):
                    caminho_dados = teste
        except:
            pass
    
    if not caminho_dados:
        root_temp = tk.Tk()
        root_temp.withdraw() 
        root_temp.attributes("-topmost", True)
        messagebox.showinfo("Bem-vindo", "Configuração Inicial:\n\nPrecisamos definir onde salvar seu Banco de Dados.\nClique em OK e escolha uma pasta segura (ex: Documentos).")
        while not caminho_dados:
            caminho_dados = filedialog.askdirectory(title="SELECIONE ONDE SALVAR OS DADOS")
            if caminho_dados:
                try:
                    with open(ARQUIVO_MEMORIA, 'w') as f:
                        json.dump({'local_banco': caminho_dados}, f)
                except: pass
            else:
                if not messagebox.askretrycancel("Atenção", "O sistema precisa de uma pasta para funcionar.\nTentar novamente?"):
                    sys.exit() 
        root_temp.destroy()

    pasta_final = os.path.join(caminho_dados, "SistemaCaixa_Dados")
    if not os.path.exists(pasta_final):
        try: os.makedirs(pasta_final)
        except: pass 
    return pasta_final

PASTA_FINAL = conectar_caminho_dados()
ARQUIVO_DB = os.path.join(PASTA_FINAL, "banco_dados_v56.db")
ARQUIVO_JSON_ANTIGO = os.path.join(PASTA_FINAL, "banco_de_dados.json")
BACKUP_1 = os.path.join(PASTA_FINAL, "backup_recente.db")
BACKUP_2 = os.path.join(PASTA_FINAL, "backup_antigo.db")
BACKUP_3 = os.path.join(PASTA_FINAL, "backup_mais_antigo.db")

def conectar_db():
    return sqlite3.connect(ARQUIVO_DB)

def realizar_backup_rotativo():
    if os.path.exists(ARQUIVO_DB):
        try:
            if os.path.exists(BACKUP_2): shutil.copy2(BACKUP_2, BACKUP_3)
            if os.path.exists(BACKUP_1): shutil.copy2(BACKUP_1, BACKUP_2)
            shutil.copy2(ARQUIVO_DB, BACKUP_1)
        except Exception as e: print(f"Alerta de Backup: {e}")

def inicializar_banco():
    if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)
    realizar_backup_rotativo()
    try:
        conn = conectar_db(); cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        conn.close()
    except:
        if os.path.exists(BACKUP_1):
            try: shutil.copy2(BACKUP_1, ARQUIVO_DB)
            except: pass
        else:
            if os.path.exists(ARQUIVO_DB):
                try: os.remove(ARQUIVO_DB)
                except: pass
    
    conn = conectar_db(); cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id TEXT PRIMARY KEY,
            data_str TEXT,
            timestamp REAL,
            desc TEXT,
            valor REAL,
            origem TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON movimentacoes (timestamp)")
    conn.commit()
    
    cursor.execute("SELECT count(*) FROM movimentacoes")
    qtd = cursor.fetchone()[0]
    if qtd == 0 and os.path.exists(ARQUIVO_JSON_ANTIGO):
        try:
            with open(ARQUIVO_JSON_ANTIGO, 'r', encoding='utf-8') as f:
                dados_antigos = json.load(f)
            novos_dados = []
            ids_gerados = set() 
            for d in dados_antigos:
                item_id = d.get('id', str(uuid.uuid4())[:8])
                while item_id in ids_gerados: item_id = str(uuid.uuid4())[:8]
                ids_gerados.add(item_id)
                dt_obj = converter_data_seguro(d['data'])
                ts = dt_obj.timestamp() if dt_obj else 0.0
                val = float(d.get('valor', 0))
                novos_dados.append((item_id, d['data'], ts, d.get('desc', ''), val, d.get('origem', 'caixa')))
            cursor.executemany("INSERT OR IGNORE INTO movimentacoes VALUES (?, ?, ?, ?, ?, ?)", novos_dados)
            conn.commit()
        except: pass
    conn.close()