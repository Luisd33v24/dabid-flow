import tkinter as tk
from datetime import datetime

# --- CONFIGURAÇÕES VISUAIS ---
COR_FUNDO = "#F0F2F5"
COR_BRANCO = "#FFFFFF"
COR_VERDE = "#27ae60"
COR_VERMELHO = "#c0392b"
COR_AZUL_RESERVA = "#2980b9" 
COR_TEXTO = "#2c3e50"
COR_CINZA_TXT = "#7f8c8d"
COR_AZUL_PONTO = "#0984e3" 

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def ler_valor_seguro(valor_str):
    if not valor_str: return None
    try:
        v = str(valor_str).replace("R$", "").replace(" ", "")
        v = v.replace('.', '').replace(',', '.') if ',' in v and '.' in v else v.replace(',', '.')
        return float(v)
    except: return None

def converter_data_seguro(data_str):
    try: return datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
    except:
        try: return datetime.strptime(data_str, "%d/%m/%Y %H:%M")
        except: return datetime.now()

def setup_placeholder(entry, texto_fantasma):
    try:
        if entry.get().strip() == "":
            entry.insert(0, texto_fantasma)
            entry.config(foreground='grey')
        
        def on_focus_in(event):
            if entry.get() == texto_fantasma:
                entry.delete(0, tk.END)
                entry.config(foreground='black')
                
        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, texto_fantasma)
                entry.config(foreground='grey')
                
        entry.bind("<FocusIn>", on_focus_in, add="+")
        entry.bind("<FocusOut>", on_focus_out, add="+")
    except Exception as e: 
        print(f"Erro Placeholder: {e}")