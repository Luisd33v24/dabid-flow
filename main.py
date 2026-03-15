import traceback

try:
    import matplotlib
    matplotlib.use('TkAgg') 

    import sqlite3
    import tkinter as tk
    from tkinter import ttk, messagebox
    import sys
    import gc
    import uuid
    from datetime import datetime, timedelta
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.ticker as ticker
    from matplotlib.ticker import FuncFormatter

    # Import do arquivo de banco de dados e utilidades
    from utilidades import *
    from banco_dados import conectar_db, inicializar_banco

    # --- SUPORTE A ALTA RESOLUÇÃO ---
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    # --- VARIÁVEIS GLOBAIS ---
    filtro_atual = "HOJE"
    data_focada = None       
    zoom_estado = None       
    pontos_scatter = None 
    ax = None
    canvas = None
    annot = None
    dados_eixo_x_cache = [] 
    dados_labels_cache = []
    historico_navegacao = [] 
    nivel_zoom_cache = None

    # --- FUNÇÕES CRUD SQL ---
    def adicionar_movimentacao_sql(tipo, origem="caixa"):
        if origem == "caixa":
            entry_v = entry_valor; entry_d = entry_desc
        else:
            entry_v = entry_valor_res; entry_d = entry_desc_res

        v_str = entry_v.get()
        valor = ler_valor_seguro(v_str)

        if valor is None or valor <= 0:
            messagebox.showwarning("Atenção", "Valor inválido."); return
        
        desc = entry_d.get().strip() or ("Aporte" if origem == "reserva" else "Venda/Serviço")
        if tipo == "saida": valor *= -1
        
        agora = datetime.now()
        novo_id = str(uuid.uuid4())[:8]
        data_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        
        conn = conectar_db(); cursor = conn.cursor()
        cursor.execute("INSERT INTO movimentacoes VALUES (?, ?, ?, ?, ?, ?)", 
                       (novo_id, data_str, agora.timestamp(), desc, valor, origem))
        conn.commit(); conn.close()
        
        entry_v.delete(0, tk.END); entry_d.delete(0, tk.END)
        
        origem_tag = origem.upper()
        tag = "lucro" if valor > 0 else "gasto"
        if origem == "reserva": tag += "_res"
        tree.insert("", 0, values=(novo_id, data_str, origem_tag, desc, formatar_moeda(valor)), tags=(tag,))
        atualizar_saldos_graficos()

    def excluir_item_sql():
        selecionado = tree.selection()
        if not selecionado: return
        item = tree.item(selecionado)
        id_alvo = str(item['values'][0])
        if messagebox.askyesno("Excluir", f"Remover ID {id_alvo}?"):
            conn = conectar_db(); cursor = conn.cursor()
            cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (id_alvo,))
            conn.commit(); conn.close()
            tree.delete(selecionado)
            atualizar_saldos_graficos()
            messagebox.showinfo("Sucesso", "Removido.")

    def carregar_dados_filtrados():
        conn = conectar_db(); cursor = conn.cursor()
        query = "SELECT * FROM movimentacoes WHERE 1=1"
        params = []
        
        f_dt = entry_filtro_data.get().strip()
        f_de = entry_filtro_desc.get().strip()
        f_va = entry_filtro_valor.get().strip()
        f_id = entry_busca_id.get().strip()
        
        if f_dt == "DD/MM/AAAA": f_dt = ""
        if f_de == "Descrição...": f_de = ""
        if f_va == "Valor...": f_va = ""

        if f_id:
            query += " AND id = ?"
            params.append(f_id)
        else:
            if f_dt:
                if len(f_dt) == 5 and '/' in f_dt: 
                    mes, ano_curto = f_dt.split('/')
                    termo_busca = f"/{mes}/20{ano_curto}"
                    query += " AND data_str LIKE ?"
                    params.append(f"%{termo_busca}%")
                elif len(f_dt) == 4 and f_dt.isdigit():
                    query += " AND data_str LIKE ?"
                    params.append(f"%/{f_dt} %")
                else:
                    query += " AND data_str LIKE ?"
                    params.append(f"%{f_dt}%")
                    
            if f_de:
                query += " AND UPPER(desc) LIKE ?"
                params.append(f"%{f_de.upper()}%")
            
            if f_va:
                try:
                    v_float = float(f_va.replace(',', '.'))
                    query += " AND ABS(valor - ?) < 0.01"
                    params.append(v_float)
                except: pass

        query += " ORDER BY timestamp DESC LIMIT 10000"
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def limpar_filtros_historico():
        entry_filtro_data.delete(0, tk.END)
        setup_placeholder(entry_filtro_data, "DD/MM/AAAA") 
        entry_filtro_desc.delete(0, tk.END)
        setup_placeholder(entry_filtro_desc, "Descrição...") 
        entry_filtro_valor.delete(0, tk.END)
        setup_placeholder(entry_filtro_valor, "Valor...") 
        entry_busca_id.delete(0, tk.END)
        atualizar_tabela()

    # --- UI UPDATES ---
    def atualizar_tabela():
        try:
            tree.pack_forget() 
            for i in tree.get_children(): tree.delete(i)
            dados = carregar_dados_filtrados()
            for row in dados:
                origem = row[5].upper()
                valor = row[4]
                tag = "lucro" if valor > 0 else "gasto"
                if origem == "RESERVA": tag += "_res"
                tree.insert("", "end", values=(row[0], row[1], origem, row[3], formatar_moeda(valor)), tags=(tag,))
            tree.pack(fill="both", expand=True, padx=10, pady=10) 
        except: pass

    def atualizar_saldos_graficos():
        conn = conectar_db(); cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM movimentacoes WHERE origem = 'caixa'")
        saldo_caixa = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(valor) FROM movimentacoes WHERE origem = 'reserva'")
        saldo_reserva = cursor.fetchone()[0] or 0.0
        conn.close()
        
        lbl_saldo.config(text=formatar_moeda(saldo_caixa), fg=COR_VERDE if saldo_caixa >= 0 else COR_VERMELHO)
        lbl_reserva_val.config(text=formatar_moeda(saldo_reserva))
        lbl_reserva_main.config(text=formatar_moeda(saldo_reserva))
        desenhar_grafico()

    # --- GRÁFICOS ---
    def obter_dados_grafico():
        global nivel_zoom_cache
        conn = conectar_db(); cursor = conn.cursor()
        agora = datetime.now()
        titulo = ""; xfmt = None
        eixo_x, eixo_y, labels = [], [], []
        
        if data_focada: modo = "DETALHADO"
        elif zoom_estado:
            if zoom_estado['tipo'] == 'ANO': modo = "MENSAL"
            elif zoom_estado['tipo'] == 'MES': modo = "DIARIO"
        else:
            if filtro_atual == "GERAL": modo = "ANUAL"
            elif filtro_atual == "HOJE": modo = "DETALHADO"
            elif "D" in filtro_atual: modo = "DIARIO"
            elif "A" in filtro_atual: modo = "MENSAL"
            else: modo = "ANUAL"

        ts_inicio = 0; ts_fim = 9999999999
        
        if modo == "DETALHADO":
            alvo = data_focada if data_focada else agora
            dt_i = alvo.replace(hour=0, minute=0, second=0, microsecond=0)
            dt_f = alvo.replace(hour=23, minute=59, second=59, microsecond=999999)
            titulo = f"Detalhado: {alvo.strftime('%d/%m/%Y')}"
            ts_inicio, ts_fim = dt_i.timestamp(), dt_f.timestamp()
            nivel_zoom_cache = "DETALHE"
            xfmt = mdates.DateFormatter('%H:%M')
            
        elif modo == "DIARIO":
            nivel_zoom_cache = "DIA"
            if zoom_estado and zoom_estado['tipo'] == 'MES':
                ano, mes = zoom_estado['ano'], zoom_estado['mes']
                titulo = f"Dias de {mes:02d}/{ano}"
                import calendar
                last = calendar.monthrange(ano, mes)[1]
                dt_i = datetime(ano, mes, 1)
                dt_f = datetime(ano, mes, last, 23, 59, 59)
                ts_inicio, ts_fim = dt_i.timestamp(), dt_f.timestamp()
            else:
                dias = int(filtro_atual.replace("D", "")) if "D" in filtro_atual else 30
                dt_i = agora - timedelta(days=dias)
                titulo = f"Últimos {dias} Dias"
                ts_inicio = dt_i.timestamp()
            xfmt = mdates.DateFormatter('%d/%m')

        elif modo == "MENSAL":
            nivel_zoom_cache = "MES"
            if zoom_estado and zoom_estado['tipo'] == 'ANO':
                ano = zoom_estado['ano']
                titulo = f"Meses do Ano {ano}"
                dt_i = datetime(ano, 1, 1); dt_f = datetime(ano, 12, 31, 23, 59, 59)
                ts_inicio, ts_fim = dt_i.timestamp(), dt_f.timestamp()
            else:
                try: anos = int(filtro_atual.replace("A", ""))
                except: anos = 1
                dt_i = agora - timedelta(days=365*anos)
                titulo = f"Histórico Mensal ({anos} Anos)"
                ts_inicio = dt_i.timestamp()
            xfmt = mdates.DateFormatter('%b/%Y')

        elif modo == "ANUAL":
            nivel_zoom_cache = "ANO"
            titulo = "Visão Geral (Por Ano)"
            ts_inicio = 0
            xfmt = mdates.DateFormatter('%Y')

        cursor.execute("SELECT timestamp, valor, desc FROM movimentacoes WHERE origem='caixa' AND timestamp BETWEEN ? AND ? ORDER BY timestamp", (ts_inicio, ts_fim))
        rows = cursor.fetchall()
        
        cursor.execute("SELECT SUM(valor) FROM movimentacoes WHERE origem='caixa' AND timestamp < ?", (ts_inicio,))
        saldo_anterior = cursor.fetchone()[0] or 0.0
        
        acumulado = float(saldo_anterior)

        if modo == "DETALHADO":
            for ts, val, desc in rows:
                acumulado += val
                dt = datetime.fromtimestamp(ts)
                eixo_x.append(dt); eixo_y.append(acumulado)
                labels.append(f"{dt.strftime('%H:%M')} - {desc}\n{formatar_moeda(val)}")
        else:
            agrupados = {}
            for ts, val, desc in rows:
                dt = datetime.fromtimestamp(ts)
                if modo == "ANUAL": chave = dt.year
                elif modo == "MENSAL": chave = (dt.year, dt.month)
                elif modo == "DIARIO": chave = dt.date()
                if chave not in agrupados: agrupados[chave] = 0.0
                agrupados[chave] += val
                
            chaves_ordenadas = sorted(agrupados.keys())
            curr_acc = acumulado
            for k in chaves_ordenadas:
                curr_acc += agrupados[k]
                if modo == "ANUAL":
                    dt_plot = datetime(k, 7, 1) 
                    lbl = f"Ano {k}\nRes: {formatar_moeda(agrupados[k])}"
                elif modo == "MENSAL":
                    dt_plot = datetime(k[0], k[1], 15)
                    lbl = f"{k[1]:02d}/{k[0]}\nRes: {formatar_moeda(agrupados[k])}"
                elif modo == "DIARIO":
                    dt_plot = datetime.combine(k, datetime.min.time())
                    lbl = f"{k.day}/{k.month}\nRes: {formatar_moeda(agrupados[k])}"
                eixo_x.append(dt_plot); eixo_y.append(curr_acc); labels.append(lbl)

        conn.close()
        return eixo_x, eixo_y, labels, titulo, xfmt

    def desenhar_grafico():
        global pontos_scatter, ax, canvas, dados_eixo_x_cache, dados_labels_cache, annot
        plt.close('all')
        if canvas: 
            try: canvas.get_tk_widget().destroy()
            except: pass
        gc.collect() 
        
        eixo_x, eixo_y, labels_texto, titulo, xfmt = obter_dados_grafico()
        dados_eixo_x_cache = eixo_x; dados_labels_cache = labels_texto 
        
        for w in frame_grafico.winfo_children(): w.destroy()

        if not eixo_x:
            tk.Label(frame_grafico, text="Sem dados para este período.", bg=COR_BRANCO, fg=COR_CINZA_TXT).pack(expand=True); return

        fig, ax = plt.subplots(figsize=(9, 4.5), facecolor=COR_BRANCO, dpi=100)
        plt.subplots_adjust(left=0.10, right=0.96, top=0.90, bottom=0.20)
        
        cor_linha = COR_VERDE if (len(eixo_y)>0 and eixo_y[-1] >= eixo_y[0]) else COR_VERMELHO
        ax.plot(eixo_x, eixo_y, color=cor_linha, linewidth=2.5, zorder=2)
        ax.fill_between(eixo_x, eixo_y, min(eixo_y), color=cor_linha, alpha=0.1, zorder=1)
        pontos_scatter = ax.scatter(eixo_x, eixo_y, color=COR_AZUL_PONTO, s=60, zorder=3, edgecolors='white', linewidth=1.5, picker=5)
        
        annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="white", ec="#555", alpha=0.9),
                            arrowprops=dict(arrowstyle="->", color="#555"), fontsize=9, zorder=10)
        annot.set_visible(False)

        if xfmt: ax.xaxis.set_major_formatter(xfmt)
        if len(eixo_x) > 15: ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
        fig.autofmt_xdate(rotation=45, ha='right')
        
        if eixo_y:
            ymin, ymax = min(eixo_y), max(eixo_y)
            margem = (ymax - ymin) * 0.15 if ymax != ymin else abs(ymax)*0.2 or 100
            ax.set_ylim(ymin - margem, ymax + margem)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
        ax.set_title(titulo, fontsize=12, color=COR_CINZA_TXT, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        
        canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.mpl_connect('pick_event', ao_clicar_ponto)
        canvas.mpl_connect('motion_notify_event', ao_passar_mouse_hover)

    # --- EVENTOS ---
    def ao_clicar_ponto(event):
        global zoom_estado, data_focada
        if data_focada: return 
        if event.ind is not None and len(event.ind) > 0:
            idx = event.ind[0]
            if idx >= len(dados_eixo_x_cache): return 
            dt_clicada = dados_eixo_x_cache[idx]
            salvar_estado_navegacao() 
            if nivel_zoom_cache == "ANO": zoom_estado = {'tipo': 'ANO', 'ano': dt_clicada.year}
            elif nivel_zoom_cache == "MES": zoom_estado = {'tipo': 'MES', 'ano': dt_clicada.year, 'mes': dt_clicada.month}
            elif nivel_zoom_cache == "DIA": data_focada = dt_clicada
            atualizar_saldos_graficos()

    def ao_passar_mouse_hover(event):
        visivel = annot.get_visible()
        if event.inaxes == ax:
            cont, ind = pontos_scatter.contains(event)
            if cont:
                idx = ind["ind"][0]
                if idx < len(dados_eixo_x_cache):
                    pos = pontos_scatter.get_offsets()[idx]
                    annot.xy = pos
                    annot.set_text(f"{dados_labels_cache[idx]}\nAcum: {formatar_moeda(pos[1])}")
                    annot.set_visible(True)
                    canvas.draw_idle()
                    canvas.get_tk_widget().config(cursor="hand2")
                return
        if visivel: annot.set_visible(False); canvas.draw_idle(); canvas.get_tk_widget().config(cursor="")

    # --- NAVEGAÇÃO E BUSCA ---
    def salvar_estado_navegacao():
        estado = {'filtro': filtro_atual, 'zoom': zoom_estado, 'foco': data_focada}
        historico_navegacao.append(estado)
        btn_voltar.pack(side="top", anchor="nw", padx=20, pady=5)

    def resetar_navegacao():
        global historico_navegacao
        historico_navegacao = []
        btn_voltar.pack_forget()

    def acao_botao_voltar():
        global filtro_atual, zoom_estado, data_focada
        if not historico_navegacao: return
        estado = historico_navegacao.pop()
        filtro_atual = estado['filtro']
        zoom_estado = estado['zoom']
        data_focada = estado['foco']
        if not historico_navegacao: btn_voltar.pack_forget()
        atualizar_saldos_graficos()

    def mudar_filtro(novo):
        global filtro_atual, data_focada, zoom_estado
        resetar_navegacao()
        filtro_atual = novo
        data_focada = None
        zoom_estado = None 
        atualizar_saldos_graficos()

    def realizar_busca_data_dashboard():
        termo = entry_busca_dash.get().strip()
        if termo == "DD/MM/AAAA" or not termo: return
        
        salvar_estado_navegacao()
        try:
            if len(termo) == 10:
                dt = datetime.strptime(termo, "%d/%m/%Y")
                global data_focada; data_focada = dt
            elif len(termo) == 7:
                dt = datetime.strptime(termo, "%m/%Y")
                global zoom_estado; zoom_estado = {'tipo': 'MES', 'ano': dt.year, 'mes': dt.month}
                data_focada = None
            elif len(termo) == 5 and '/' in termo:
                dt = datetime.strptime(termo, "%m/%y")
                zoom_estado = {'tipo': 'MES', 'ano': dt.year, 'mes': dt.month}
                data_focada = None
            elif len(termo) == 4 and termo.isdigit():
                ano = int(termo)
                zoom_estado = {'tipo': 'ANO', 'ano': ano}
                data_focada = None
            else:
                raise ValueError()
            atualizar_saldos_graficos()
        except:
            messagebox.showerror("Erro de Busca", "Formatos aceitos:\n- 15/05/2024 (Dia)\n- 05/2024 (Mês)\n- 2024 (Ano)")

    # --- INICIALIZAÇÃO DA UI ---
    root = tk.Tk()
    root.title("Sistema de Caixa - V80")
    def on_close(): plt.close('all'); root.destroy(); sys.exit()
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.geometry("1024x650"); 
    try: root.state('zoomed')
    except: pass
    style = ttk.Style(); style.theme_use('clam')

    inicializar_banco()

    abas = ttk.Notebook(root); abas.pack(fill="both", expand=True)
    tab_dash = tk.Frame(abas, bg=COR_FUNDO); abas.add(tab_dash, text="   📊 Painel   ")
    tab_reserva = tk.Frame(abas, bg=COR_BRANCO); abas.add(tab_reserva, text="   🛡️ Reserva   ")
    tab_hist = tk.Frame(abas, bg=COR_BRANCO); abas.add(tab_hist, text="   📝 Histórico   ")

    # HEADER
    header = tk.Frame(tab_dash, bg=COR_BRANCO, padx=20, pady=10); header.pack(fill="x", padx=10, pady=10)
    fr_left = tk.Frame(header, bg=COR_BRANCO); fr_left.pack(side="left")
    tk.Label(fr_left, text="CAIXA", bg=COR_BRANCO, fg=COR_CINZA_TXT).pack(anchor="w")
    lbl_saldo = tk.Label(fr_left, text="---", font=("Segoe UI", 24, "bold"), bg=COR_BRANCO); lbl_saldo.pack(anchor="w")
    fr_mid = tk.Frame(header, bg=COR_BRANCO, padx=40); fr_mid.pack(side="left")
    tk.Label(fr_mid, text="RESERVA", bg=COR_BRANCO, fg=COR_CINZA_TXT).pack(anchor="w")
    lbl_reserva_val = tk.Label(fr_mid, text="---", font=("Segoe UI", 14, "bold"), fg=COR_AZUL_RESERVA, bg=COR_BRANCO); lbl_reserva_val.pack(anchor="w")

    fr_busca = tk.Frame(header, bg=COR_FUNDO, padx=10, pady=5); fr_busca.pack(side="right")
    entry_busca_dash = ttk.Entry(fr_busca, width=15); entry_busca_dash.pack(side="left", padx=5)
    setup_placeholder(entry_busca_dash, "DD/MM/AAAA") 
    tk.Button(fr_busca, text="🔍", command=realizar_busca_data_dashboard, bg=COR_AZUL_PONTO, fg="white", relief="flat").pack(side="left")

    btn_voltar = tk.Button(tab_dash, text="⬅ Voltar Nível", bg=COR_CINZA_TXT, fg=COR_BRANCO, command=acao_botao_voltar, relief="flat")
    bar_filtros = tk.Frame(tab_dash, bg=COR_FUNDO); bar_filtros.pack(fill="x", padx=10)
    for t,c in [("HOJE","HOJE"),("7 Dias","7D"),("30 Dias","30D"),("1 Ano","1A"),("2 Anos","2A"),("GERAL","GERAL")]:
        tk.Button(bar_filtros, text=t, command=lambda x=c: mudar_filtro(x), bg=COR_BRANCO, relief="flat", padx=8, pady=2).pack(side="left", padx=1)

    fr_input = tk.Frame(tab_dash, bg=COR_BRANCO, pady=5) 
    fr_input.pack(fill="x", side="bottom")

    frame_grafico = tk.Frame(tab_dash, bg=COR_BRANCO)
    frame_grafico.pack(fill="both", expand=True, padx=10, pady=5)

    c1 = tk.Frame(fr_input, bg=COR_BRANCO); c1.pack()
    
    tk.Label(c1, text="Descrição:", bg=COR_BRANCO).grid(row=0, column=0)
    entry_desc = ttk.Entry(c1, width=25); entry_desc.grid(row=0, column=1, padx=5)
    tk.Label(c1, text="R$:", bg=COR_BRANCO).grid(row=0, column=2)
    entry_valor = ttk.Entry(c1, width=12); entry_valor.grid(row=0, column=3, padx=5)
    tk.Button(c1, text=" RECEITA (+) ", bg=COR_VERDE, fg=COR_BRANCO, font=("Bold", 9), command=lambda: adicionar_movimentacao_sql("entrada")).grid(row=0, column=4, padx=5)
    tk.Button(c1, text=" DESPESA (-) ", bg=COR_VERMELHO, fg=COR_BRANCO, font=("Bold", 9), command=lambda: adicionar_movimentacao_sql("saida")).grid(row=0, column=5)

    # HIST LAYOUT
    fr_top_hist = tk.Frame(tab_hist, bg=COR_BRANCO, pady=5); fr_top_hist.pack(fill="x")
    fr_1 = tk.Frame(fr_top_hist, bg=COR_BRANCO); fr_1.pack(fill="x", padx=10, pady=2)
    tk.Label(fr_1, text="ID:", bg=COR_BRANCO).pack(side="left")
    entry_busca_id = ttk.Entry(fr_1, width=15); entry_busca_id.pack(side="left", padx=5)
    tk.Button(fr_1, text="Busca ID", command=atualizar_tabela, bg=COR_AZUL_PONTO, fg="white", relief="flat").pack(side="left")

    fr_2 = tk.Frame(fr_top_hist, bg="#f9f9f9", padx=5, pady=2); fr_2.pack(fill="x", padx=10)
    tk.Label(fr_2, text="Filtros:", bg="#f9f9f9", font=("Arial",9,"bold")).pack(side="left")
    
    entry_filtro_data = ttk.Entry(fr_2, width=12); entry_filtro_data.pack(side="left", padx=2)
    setup_placeholder(entry_filtro_data, "DD/MM/AAAA") 
    entry_filtro_desc = ttk.Entry(fr_2, width=20); entry_filtro_desc.pack(side="left", padx=2)
    setup_placeholder(entry_filtro_desc, "Descrição...") 
    entry_filtro_valor = ttk.Entry(fr_2, width=10); entry_filtro_valor.pack(side="left", padx=2)
    setup_placeholder(entry_filtro_valor, "Valor...") 

    tk.Button(fr_2, text="Filtrar", command=atualizar_tabela, bg=COR_CINZA_TXT, fg="white", relief="flat").pack(side="left", padx=5)
    tk.Button(fr_2, text="Limpar", command=limpar_filtros_historico, bg=COR_BRANCO, relief="flat").pack(side="left")
    tk.Button(fr_2, text="🗑 Apagar", bg=COR_VERMELHO, fg=COR_BRANCO, command=excluir_item_sql).pack(side="right")

    cols = ('id', 'd', 'c', 'de', 'v')
    tree = ttk.Treeview(tab_hist, columns=cols, show='headings')
    tree.heading('id', text='ID'); tree.column('id', width=60, anchor="center")
    tree.heading('d', text='Data'); tree.column('d', width=130, anchor="center")
    tree.heading('c', text='Conta'); tree.column('c', width=80, anchor="center")
    tree.heading('de', text='Descrição'); tree.column('de', width=300, anchor="w")
    tree.heading('v', text='Valor'); tree.column('v', width=100, anchor="e")
    tree.tag_configure('lucro', foreground=COR_VERDE); tree.tag_configure('gasto', foreground=COR_VERMELHO); tree.tag_configure('lucro_res', foreground=COR_AZUL_RESERVA)
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    sb = ttk.Scrollbar(tab_hist, orient="vertical", command=tree.yview); sb.pack(side="right", fill="y"); tree.configure(yscrollcommand=sb.set)

    # RESERVA LAYOUT
    fr_res_center = tk.Frame(tab_reserva, bg=COR_BRANCO); fr_res_center.pack(expand=True)
    tk.Label(fr_res_center, text="Total Reserva", fg=COR_CINZA_TXT, bg=COR_BRANCO).pack()
    lbl_reserva_main = tk.Label(fr_res_center, text="---", font=("Segoe UI", 36, "bold"), fg=COR_AZUL_RESERVA, bg=COR_BRANCO); lbl_reserva_main.pack(pady=10)
    fr_act_res = tk.Frame(fr_res_center, bg="#ecf0f1", padx=20, pady=20); fr_act_res.pack(pady=20)
    tk.Label(fr_act_res, text="Desc:", bg="#ecf0f1").grid(row=0, column=0)
    entry_desc_res = ttk.Entry(fr_act_res, width=20); entry_desc_res.grid(row=0, column=1, padx=5)
    tk.Label(fr_act_res, text="Val:", bg="#ecf0f1").grid(row=0, column=2)
    entry_valor_res = ttk.Entry(fr_act_res, width=12); entry_valor_res.grid(row=0, column=3, padx=5)
    tk.Button(fr_act_res, text="GUARDAR", bg=COR_AZUL_RESERVA, fg=COR_BRANCO, command=lambda: adicionar_movimentacao_sql("entrada", "reserva")).grid(row=1, column=0, columnspan=2, pady=10, sticky="we")
    tk.Button(fr_act_res, text="RESGATAR", bg="#e67e22", fg=COR_BRANCO, command=lambda: adicionar_movimentacao_sql("saida", "reserva")).grid(row=1, column=2, columnspan=2, pady=10, sticky="we")

    atualizar_saldos_graficos(); atualizar_tabela()
    root.mainloop()

except Exception:
    traceback.print_exc()
    input("\nERRO CRÍTICO ENCONTRADO. Pressione ENTER para sair...")