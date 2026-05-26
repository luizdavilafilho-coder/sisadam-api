import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os
from datetime import datetime

# --- Configuração de Caminhos Unificados do SISADAM ---
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
ARQUIVO_DB = PASTA_BANCO / "visitantes.db"
ARQUIVO_DB_MORADORES = PASTA_BANCO / "dados_moradores.db" # Banco para a busca inteligente

class BancoVisitantes(ctk.CTkFrame):
    def __init__(self, master, nivel="OPERADOR", **kwargs):
        super().__init__(master, **kwargs)
        self.cor_destaque = "#F57C00"
        self.id_em_edicao = None
        self.nivel = nivel 
        PASTA_BANCO.mkdir(parents=True, exist_ok=True)
        
        self.criar_banco()
        self.montar_interface()
        self.aplicar_permissoes()
        self.carregar_dados()

    def criar_banco(self):
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute('''CREATE TABLE IF NOT EXISTS visitantes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            visitante TEXT, 
                            documento TEXT,
                            bloco TEXT,
                            apartamento TEXT,
                            autorizado_por TEXT,
                            hora_entrada TEXT,
                            hora_saida TEXT)''')
        conn.commit()
        conn.close()

    def fechar_ciclo_diario(self):
        """Exportação automática dos visitantes para o Cofre à meia-noite"""
        try:
            import pandas as pd
            import sqlite3
            import pathlib
            from datetime import datetime, timedelta
            
            # Caminhos específicos para Visitantes (Padrão SISADAM)
            p_base = pathlib.Path.home() / "Documents" / "SISADAM"
            p_banco = p_base / "Arquivos_Banco" / "visitantes.db"
            p_cofre = p_base / "Cofre_Backup" / "Visitantes"
            p_cofre.mkdir(parents=True, exist_ok=True)
            
            # Data de referência (ontem)
            ontem = (datetime.now() - timedelta(days=1)).strftime('%d-%m-%Y')
            caminho_excel = p_cofre / f"Relatorio_Visitantes_{ontem}.xlsx"
            
            # Conecta e gera o backup em Excel
            conn = sqlite3.connect(str(p_banco))
            df = pd.read_sql_query("SELECT * FROM visitantes", conn)
            df.to_excel(caminho_excel, index=False)
            conn.close()
            
            # Limpa a interface para o novo dia
            self.carregar_dados()
            self.reset_total()
            
            print(f"Backup de Visitantes concluído: {caminho_excel}")
        except Exception as e:
            print(f"Erro no backup automático de visitantes: {e}")

    def montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.label_titulo = ctk.CTkLabel(self, text=f"SISADAM - CONTROLE DE VISITANTES [{self.nivel}]", font=("Roboto Mono", 20, "bold"), text_color=self.cor_destaque)
        self.label_titulo.grid(row=0, column=0, pady=(10, 0))

        # --- QUADRO DE FORMULÁRIO (100% LARGURA, SEM DOCUMENTO E SEM FOTO) ---
        self.frame_form = ctk.CTkFrame(self, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333333")
        self.frame_form.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        estilo_in = {"fg_color": "white", "text_color": "black", "placeholder_text_color": "gray"}

        # LINHA 1: Visitante e Destino
        self.ent_visitante = ctk.CTkEntry(self.frame_form, placeholder_text="NOME DO VISITANTE", width=350, **estilo_in)
        self.ent_visitante.grid(row=0, column=0, padx=10, pady=15, sticky="w")

        self.frame_destino = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_destino.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        # Gatilho de busca cruzada no Bloco
        self.ent_bloco = ctk.CTkComboBox(self.frame_destino, values=["BLOCO A", "BLOCO B"], width=120, fg_color="white", text_color="black", command=self.buscar_morador_autorizador)
        self.ent_bloco.set("BLOCO")
        self.ent_bloco.pack(side="left", padx=(0, 10))

        # Gatilho de busca cruzada no Apto
        self.ent_apt = ctk.CTkEntry(self.frame_destino, placeholder_text="APTO", width=100, **estilo_in)
        self.ent_apt.pack(side="left", padx=(0, 10))
        self.ent_apt.bind("<KeyRelease>", self.buscar_morador_autorizador)

        # ComboBox Inteligente para Autorização
        self.cb_autorizado = ctk.CTkComboBox(self.frame_form, values=["AUTORIZADO POR..."], width=300, fg_color="white", text_color="black")
        self.cb_autorizado.set("AUTORIZADO POR...")
        self.cb_autorizado.grid(row=0, column=2, padx=10, pady=15, sticky="ew")

        # --- BARRA DE AÇÕES INTEGRADA ---
        self.frame_acoes = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_acoes.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 15), sticky="ew")

        self.btn_novo = ctk.CTkButton(self.frame_acoes, text="+ NOVO REGISTRO", fg_color="#2E7D32", hover_color="#1B5E20", text_color="white", font=("Roboto Mono", 11, "bold"), command=self.reset_total, width=140)
        self.btn_novo.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(self.frame_acoes, text="SALVAR / ENTRADA", fg_color=self.cor_destaque, text_color="black", font=("Roboto Mono", 11, "bold"), command=self.salvar_registro, width=150)
        self.btn_salvar.pack(side="left", padx=5)

        self.btn_saida = ctk.CTkButton(self.frame_acoes, text="REGISTRAR SAÍDA", fg_color="#2E7D32", hover_color="#1B5E20", text_color="white", font=("Roboto Mono", 11, "bold"), command=self.registrar_saida, width=140)
        self.btn_saida.pack(side="left", padx=5)

        self.btn_editar = ctk.CTkButton(self.frame_acoes, text="EDITAR REGISTRO", fg_color="#1E88E5", text_color="white", font=("Roboto Mono", 11, "bold"), command=self.carregar_edicao, width=140)
        self.btn_editar.pack(side="left", padx=5)

        self.btn_exportar = ctk.CTkButton(self.frame_acoes, text="📊 EXPORTAR HOJE", fg_color="#1D6F42", hover_color="#144C2D", text_color="white", font=("Roboto Mono", 11, "bold"), command=self.exportar_relatorio, width=150)
        self.btn_exportar.pack(side="right", padx=5)

        self.btn_deletar = ctk.CTkButton(self.frame_acoes, text="DELETAR", fg_color="#D32F2F", hover_color="#B71C1C", text_color="white", font=("Roboto Mono", 11, "bold"), command=self.deletar_registro, width=100)
        self.btn_deletar.pack(side="right", padx=5)

        # --- TABELA ---
        self.frame_tabela = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tabela.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=28, fieldbackground="white", font=("Arial", 9))
        style.map("Treeview", background=[('selected', self.cor_destaque)], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background="#222", foreground="white", relief="flat", font=("Arial", 9, "bold"))

        # Removido 'Documento' da visualização para ficar mais limpo
        colunas = ("ID", "Visitante", "Bloco", "Apto", "Autorizado Por", "Entrada", "Saída")
        self.tabela = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        
        sc_v = ttk.Scrollbar(self.frame_tabela, orient="vertical", command=self.tabela.yview)
        sc_h = ttk.Scrollbar(self.frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=sc_v.set, xscrollcommand=sc_h.set)

        for col in colunas:
            self.tabela.heading(col, text=col)
            if col == "Visitante": largura = 250
            elif col == "Autorizado Por": largura = 200
            elif col in ["Entrada", "Saída"]: largura = 130
            elif col in ["ID", "Apto"]: largura = 60
            elif col == "Bloco": largura = 90
            else: largura = 100
            self.tabela.column(col, width=largura, anchor="center" if col != "Visitante" else "w")
            
        sc_v.pack(side="right", fill="y")
        sc_h.pack(side="bottom", fill="x")
        self.tabela.pack(side="left", fill="both", expand=True)

    # --- FUNÇÃO DE BUSCA CRUZADA DE MORADORES ---
    def buscar_morador_autorizador(self, event=None):
        bloco = self.ent_bloco.get()
        apto = self.ent_apt.get().strip()

        if bloco != "BLOCO" and apto:
            try:
                conn = sqlite3.connect(str(ARQUIVO_DB_MORADORES))
                cur = conn.execute("SELECT nome_morador FROM moradores WHERE bloco=? AND apartamento=?", (bloco, apto))
                resultados = [r[0] for r in cur.fetchall()]
                conn.close()

                if resultados:
                    self.cb_autorizado.configure(values=resultados)
                    self.cb_autorizado.set(resultados[0])
                else:
                    self.cb_autorizado.configure(values=["NÃO ENCONTRADO"])
                    self.cb_autorizado.set("NÃO ENCONTRADO")
            except Exception:
                self.cb_autorizado.configure(values=["ERRO DE BUSCA"])
        else:
            self.cb_autorizado.configure(values=["AUTORIZADO POR..."])
            self.cb_autorizado.set("AUTORIZADO POR...")

    def aplicar_permissoes(self):
        cor_bloqueado = "#444444"
        if self.nivel == "OPERADOR":
            self.btn_editar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_deletar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_exportar.configure(state="disabled", fg_color=cor_bloqueado)
        elif self.nivel == "ADMIN":
            self.btn_editar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_deletar.configure(state="disabled", fg_color=cor_bloqueado)

    def reset_total(self):
        self.limpar_campos()
        self.ent_bloco.set("BLOCO")
        self.cb_autorizado.configure(values=["AUTORIZADO POR..."]); self.cb_autorizado.set("AUTORIZADO POR...")
        self.id_em_edicao = None
        self.btn_salvar.configure(text="SALVAR / ENTRADA")

    def salvar_registro(self):
        autorizador = self.cb_autorizado.get().upper()
        if autorizador in ["AUTORIZADO POR...", "NÃO ENCONTRADO"]:
            autorizador = ""

        # O índice 1 está vazio ("") porque removemos o documento, mas mantemos no banco para não corromper dados antigos
        dados = (
            self.ent_visitante.get().strip().upper(),
            "", # Campo documento substituído por string vazia
            self.ent_bloco.get() if self.ent_bloco.get() != "BLOCO" else "",
            self.ent_apt.get().strip().upper(),
            autorizador
        )

        if not dados[0] or not dados[4]:
            messagebox.showwarning("Aviso", "Preencha o NOME DO VISITANTE e QUEM AUTORIZOU.")
            return

        conn = sqlite3.connect(str(ARQUIVO_DB))
        if self.id_em_edicao:
            if self.nivel != "MASTER":
                messagebox.showerror("Erro", "Ação permitida apenas para nível MASTER.")
                conn.close()
                return
            conn.execute('''UPDATE visitantes SET visitante=?, documento=?, bloco=?, apartamento=?, autorizado_por=? WHERE id=?''', 
                         (*dados, self.id_em_edicao))
            messagebox.showinfo("Sucesso", "Registro atualizado.")
        else:
            hora_entrada = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute('''INSERT INTO visitantes (visitante, documento, bloco, apartamento, autorizado_por, hora_entrada, hora_saida) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''', (*dados, hora_entrada, "---"))
            messagebox.showinfo("Entrada", f"Visitante liberado às {hora_entrada}")
            
        conn.commit()
        conn.close()
        self.reset_total()
        self.carregar_dados()

    def registrar_saida(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um visitante na tabela.")
            return
        
        id_reg = self.tabela.item(selecionado[0])['values'][0]
        saida_atual = self.tabela.item(selecionado[0])['values'][6]
        
        if saida_atual != "---":
            messagebox.showinfo("Aviso", "Saída já registrada.")
            return

        hora_saida = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("UPDATE visitantes SET hora_saida=? WHERE id=?", (hora_saida, id_reg))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saída", f"Saída registrada às {hora_saida}")
        self.carregar_dados()

    def carregar_edicao(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Ação permitida apenas para nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        
        id_reg = self.tabela.item(selecionado[0])['values'][0]
        
        # Busca no banco para recuperar todos os dados (incluindo o documento oculto se existir)
        conn = sqlite3.connect(str(ARQUIVO_DB))
        res = conn.execute("SELECT * FROM visitantes WHERE id=?", (id_reg,)).fetchone()
        conn.close()

        if res:
            self.id_em_edicao = res[0]
            self.limpar_campos()
            self.ent_visitante.insert(0, res[1])
            self.ent_bloco.set(res[3] if res[3] else "BLOCO")
            self.ent_apt.insert(0, str(res[4]) if res[4] else "")
            
            # Atualiza a caixa de autorizador
            self.cb_autorizado.set(res[5] if res[5] else "AUTORIZADO POR...")
            
            self.btn_salvar.configure(text="ATUALIZAR DADOS")

    def deletar_registro(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Ação permitida apenas para nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        if messagebox.askyesno("Confirmação", "Excluir permanentemente este registro?"):
            conn = sqlite3.connect(str(ARQUIVO_DB))
            conn.execute("DELETE FROM visitantes WHERE id=?", (self.tabela.item(selecionado[0])['values'][0],))
            conn.commit()
            conn.close()
            self.carregar_dados()

    def exportar_relatorio(self):
        if self.nivel == "OPERADOR": return
        try:
            import pandas as pd
            pasta_export = PASTA_BASE / "Arquivos_Excel"
            pasta_export.mkdir(parents=True, exist_ok=True)
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            
            conn = sqlite3.connect(str(ARQUIVO_DB))
            # Exporta tudo do banco
            df = pd.read_sql_query("SELECT id, visitante, documento, bloco, apartamento, autorizado_por, hora_entrada, hora_saida FROM visitantes WHERE hora_entrada LIKE ? ORDER BY id DESC", conn, params=(f"{data_hoje}%",))
            conn.close()

            if df.empty:
                messagebox.showinfo("Aviso", "Não há entradas hoje para exportar.")
                return

            df.columns = ["ID", "Nome do Visitante", "Documento", "Bloco", "Apartamento", "Autorizado Por", "Entrada", "Saída"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = pasta_export / f"Relatorio_Visitantes_Hoje_{timestamp}.xlsx"
            df.to_excel(str(caminho), index=False)
            if messagebox.askyesno("Sucesso", "Deseja abrir a planilha agora?"):
                os.startfile(str(caminho))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar: {e}")

    def limpar_campos(self):
        self.ent_visitante.delete(0, 'end')
        self.ent_apt.delete(0, 'end')

    def carregar_dados(self):
        for i in self.tabela.get_children(): self.tabela.delete(i)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        # Removemos o índice do documento (2) da visualização da Treeview
        cursor = conn.execute("SELECT id, visitante, bloco, apartamento, autorizado_por, hora_entrada, hora_saida FROM visitantes WHERE hora_entrada LIKE ? ORDER BY id DESC", (f"{data_hoje}%",))
        for r in cursor.fetchall():
            linha = list(r)
            for i in range(len(linha)):
                if not linha[i] or str(linha[i]).strip() == "": linha[i] = "-"
            self.tabela.insert("", "end", values=linha)
        conn.close()