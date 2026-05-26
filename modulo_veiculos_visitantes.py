import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os
from datetime import datetime

# --- Configuração de Caminhos Unificados do SISADAM ---
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
ARQUIVO_DB = PASTA_BANCO / "veiculos_visitantes.db"
ARQUIVO_DB_MORADORES = PASTA_BANCO / "dados_moradores.db" # Adicionado para a busca cruzada

class BancoVeiculosVisitantes(ctk.CTkFrame):
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
        conn.execute('''CREATE TABLE IF NOT EXISTS veiculos_visitantes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            visitante TEXT, 
                            apartamento TEXT,
                            bloco TEXT,
                            marca TEXT,
                            modelo TEXT,
                            tipo TEXT,
                            cor TEXT,
                            placa TEXT,
                            autorizado_por TEXT,
                            hora_entrada TEXT,
                            hora_saida TEXT)''')
        conn.commit()
        conn.close()

    def fechar_ciclo_diario(self):
        """Exportação automática dos veículos de visitantes para o Cofre à meia-noite"""
        try:
            import pandas as pd
            import sqlite3
            import pathlib
            from datetime import datetime, timedelta
            
            # Caminhos específicos (Padrão SISADAM)
            p_base = pathlib.Path.home() / "Documents" / "SISADAM"
            p_banco = p_base / "Arquivos_Banco" / "veiculos_visitantes.db"
            p_cofre = p_base / "Cofre_Backup" / "Veiculos_Visitantes"
            p_cofre.mkdir(parents=True, exist_ok=True)
            
            # Data de referência (ontem)
            ontem = (datetime.now() - timedelta(days=1)).strftime('%d-%m-%Y')
            caminho_excel = p_cofre / f"Relatorio_Veiculos_{ontem}.xlsx"
            
            # Conecta e gera o backup
            conn = sqlite3.connect(str(p_banco))
            df = pd.read_sql_query("SELECT * FROM veiculos_visitantes", conn)
            df.to_excel(caminho_excel, index=False)
            conn.close()
            
            # Reseta a interface para o novo dia
            self.carregar_dados()
            self.reset_total()
            
            print(f"Fechamento 24h de Veículos concluído: {caminho_excel}")
        except Exception as e:
            print(f"Erro no backup automático de veículos: {e}")

    def montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.label_titulo = ctk.CTkLabel(self, text=f"SISADAM - VEÍCULOS DE VISITANTES [{self.nivel}]", font=("Roboto Mono", 20, "bold"), text_color=self.cor_destaque)
        self.label_titulo.grid(row=0, column=0, pady=(10, 0))

        # --- SEÇÃO 1: FORMULÁRIO (LARGURA TOTAL, SEM FOTO) ---
        self.frame_form = ctk.CTkFrame(self, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333333")
        self.frame_form.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        estilo_in = {"fg_color": "white", "text_color": "black", "placeholder_text_color": "gray"}

        # LINHA 1: Visitante e Destino
        self.ent_visitante = ctk.CTkEntry(self.frame_form, placeholder_text="NOME DO VISITANTE", width=300, **estilo_in)
        self.ent_visitante.grid(row=0, column=0, padx=10, pady=15, sticky="w")

        # Gatilho de busca cruzada no Bloco
        self.ent_bloco = ctk.CTkComboBox(self.frame_form, values=["BLOCO A", "BLOCO B", "N/A"], width=120, fg_color="white", text_color="black", command=self.buscar_morador_autorizador)
        self.ent_bloco.set("BLOCO")
        self.ent_bloco.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        # Gatilho de busca cruzada no Apto
        self.ent_apt = ctk.CTkEntry(self.frame_form, placeholder_text="APTO", width=100, **estilo_in)
        self.ent_apt.grid(row=0, column=2, padx=10, pady=15, sticky="w")
        self.ent_apt.bind("<KeyRelease>", self.buscar_morador_autorizador)

        # Alterado para ComboBox Inteligente
        self.cb_autorizado = ctk.CTkComboBox(self.frame_form, values=["AUTORIZADO POR..."], width=250, fg_color="white", text_color="black")
        self.cb_autorizado.set("AUTORIZADO POR...")
        self.cb_autorizado.grid(row=0, column=3, padx=10, pady=15, sticky="ew")

        # LINHA 2: Características do Veículo
        self.frame_veiculo = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_veiculo.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="w")

        self.ent_marca = ctk.CTkEntry(self.frame_veiculo, placeholder_text="MARCA", width=120, **estilo_in)
        self.ent_marca.pack(side="left", padx=(0, 10))

        self.ent_modelo = ctk.CTkEntry(self.frame_veiculo, placeholder_text="MODELO", width=150, **estilo_in)
        self.ent_modelo.pack(side="left", padx=(0, 10))

        self.ent_tipo = ctk.CTkComboBox(self.frame_veiculo, values=["AUTOMÓVEL", "PICKUP/CAMINHONETE", "JIPE", "SUV"], width=180, fg_color="white", text_color="black")
        self.ent_tipo.set("TIPO")
        self.ent_tipo.pack(side="left", padx=(0, 10))

        self.ent_cor = ctk.CTkEntry(self.frame_veiculo, placeholder_text="COR", width=100, **estilo_in)
        self.ent_cor.pack(side="left", padx=(0, 10))

        self.ent_placa = ctk.CTkEntry(self.frame_veiculo, placeholder_text="PLACA", width=120, **estilo_in)
        self.ent_placa.pack(side="left")

        # --- BARRA DE AÇÕES INTEGRADA ---
        self.frame_acoes = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_acoes.grid(row=2, column=0, columnspan=4, padx=10, pady=(15, 15), sticky="ew")

        self.btn_novo = ctk.CTkButton(self.frame_acoes, text="+ NOVO REGISTRO", fg_color="#555", font=("Roboto Mono", 11, "bold"), command=self.reset_total, width=130)
        self.btn_novo.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(self.frame_acoes, text="SALVAR / ENTRADA", fg_color=self.cor_destaque, text_color="black", font=("Roboto Mono", 11, "bold"), command=self.salvar_registro, width=140)
        self.btn_salvar.pack(side="left", padx=5)

        self.btn_saida = ctk.CTkButton(self.frame_acoes, text="REGISTRAR SAÍDA", fg_color="#2E7D32", font=("Roboto Mono", 11, "bold"), command=self.registrar_saida, width=130)
        self.btn_saida.pack(side="left", padx=5)

        self.btn_editar = ctk.CTkButton(self.frame_acoes, text="EDITAR REGISTRO", fg_color="#1E88E5", font=("Roboto Mono", 11, "bold"), command=self.carregar_edicao, width=130)
        self.btn_editar.pack(side="left", padx=5)

        self.btn_exportar = ctk.CTkButton(self.frame_acoes, text="📊 EXPORTAR HOJE", fg_color="#1D6F42", font=("Roboto Mono", 11, "bold"), command=self.exportar_relatorio, width=140)
        self.btn_exportar.pack(side="right", padx=5)

        self.btn_deletar = ctk.CTkButton(self.frame_acoes, text="DELETAR", fg_color="#D32F2F", font=("Roboto Mono", 11, "bold"), command=self.deletar_registro, width=100)
        self.btn_deletar.pack(side="right", padx=5)

        # --- SEÇÃO 2: TABELA ---
        self.frame_tabela = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tabela.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=25, fieldbackground="white", font=("Arial", 9))
        style.map("Treeview", background=[('selected', self.cor_destaque)], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background="#222", foreground="white", relief="flat", font=("Arial", 9, "bold"))

        colunas = ("ID", "Visitante", "Apto", "Bloco", "Marca", "Modelo", "Tipo", "Cor", "Placa", "Autorizado Por", "Entrada", "Saída")
        self.tabela = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        
        sc_v = ttk.Scrollbar(self.frame_tabela, orient="vertical", command=self.tabela.yview)
        sc_h = ttk.Scrollbar(self.frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=sc_v.set, xscrollcommand=sc_h.set)

        for col in colunas:
            self.tabela.heading(col, text=col)
            if col == "Visitante": largura = 180
            elif col in ["Marca", "Modelo", "Autorizado Por"]: largura = 120
            elif col in ["Entrada", "Saída"]: largura = 115
            elif col in ["ID", "Apto", "Cor"]: largura = 50
            elif col in ["Bloco", "Placa"]: largura = 80
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
        self.ent_tipo.set("TIPO")
        self.cb_autorizado.configure(values=["AUTORIZADO POR..."]); self.cb_autorizado.set("AUTORIZADO POR...")
        self.id_em_edicao = None
        self.btn_salvar.configure(text="SALVAR / ENTRADA")

    def salvar_registro(self):
        autorizador = self.cb_autorizado.get().upper()
        if autorizador in ["AUTORIZADO POR...", "NÃO ENCONTRADO"]:
            autorizador = ""

        dados = (
            self.ent_visitante.get().strip().upper(),
            self.ent_apt.get().strip().upper(),
            self.ent_bloco.get() if self.ent_bloco.get() != "BLOCO" else "",
            self.ent_marca.get().strip().upper(),
            self.ent_modelo.get().strip().upper(),
            self.ent_tipo.get() if self.ent_tipo.get() != "TIPO" else "",
            self.ent_cor.get().strip().upper(),
            self.ent_placa.get().strip().upper(),
            autorizador
        )

        if not dados[0] or not dados[7] or not dados[8]:
            messagebox.showwarning("Aviso", "NOME, PLACA e AUTORIZADO POR são obrigatórios.")
            return

        conn = sqlite3.connect(str(ARQUIVO_DB))
        if self.id_em_edicao:
            if self.nivel != "MASTER":
                messagebox.showerror("Erro", "Acesso restrito ao nível MASTER.")
                conn.close()
                return
            conn.execute('''UPDATE veiculos_visitantes SET visitante=?, apartamento=?, bloco=?, marca=?, modelo=?, tipo=?, cor=?, placa=?, autorizado_por=? WHERE id=?''', 
                         (*dados, self.id_em_edicao))
            messagebox.showinfo("Sucesso", "Registro atualizado.")
        else:
            hora_entrada = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute('''INSERT INTO veiculos_visitantes (visitante, apartamento, bloco, marca, modelo, tipo, cor, placa, autorizado_por, hora_entrada, hora_saida) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (*dados, hora_entrada, "---"))
            messagebox.showinfo("Entrada", f"Veículo liberado às {hora_entrada}")
            
        conn.commit()
        conn.close()
        self.reset_total()
        self.carregar_dados()

    def registrar_saida(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um veículo.")
            return
        valores = self.tabela.item(selecionado[0])['values']
        if valores[11] != "---":
            messagebox.showinfo("Aviso", "Saída já registrada.")
            return

        hora_saida = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("UPDATE veiculos_visitantes SET hora_saida=? WHERE id=?", (hora_saida, valores[0]))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saída", f"Saída registrada às {hora_saida}")
        self.carregar_dados()

    def carregar_edicao(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Acesso restrito ao nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        
        valores = self.tabela.item(selecionado[0])['values']
        self.id_em_edicao = valores[0]
        self.limpar_campos()
        self.ent_visitante.insert(0, valores[1])
        self.ent_apt.insert(0, str(valores[2]) if valores[2] != "-" else "")
        self.ent_bloco.set(valores[3] if valores[3] != "-" else "BLOCO")
        self.ent_marca.insert(0, valores[4])
        self.ent_modelo.insert(0, valores[5])
        self.ent_tipo.set(valores[6] if str(valores[6]) != "-" else "TIPO")
        self.ent_cor.insert(0, valores[7])
        self.ent_placa.insert(0, valores[8])
        
        self.cb_autorizado.set(valores[9] if valores[9] != "-" else "AUTORIZADO POR...")
        
        self.btn_salvar.configure(text="ATUALIZAR DADOS")

    def deletar_registro(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Acesso restrito ao nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        if messagebox.askyesno("Confirmação", "Excluir permanentemente este registro?"):
            conn = sqlite3.connect(str(ARQUIVO_DB))
            conn.execute("DELETE FROM veiculos_visitantes WHERE id=?", (self.tabela.item(selecionado[0])['values'][0],))
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
            df = pd.read_sql_query("SELECT * FROM veiculos_visitantes WHERE hora_entrada LIKE ? ORDER BY id DESC", conn, params=(f"{data_hoje}%",))
            conn.close()

            if df.empty:
                messagebox.showinfo("Aviso", "Sem entradas hoje para exportar.")
                return

            df.columns = ["ID", "Visitante", "Apto", "Bloco", "Marca", "Modelo", "Tipo", "Cor", "Placa", "Autorizado Por", "Entrada", "Saída"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = pasta_export / f"Relatorio_Veic_Visitantes_{timestamp}.xlsx"
            df.to_excel(str(caminho), index=False)
            if messagebox.askyesno("Sucesso", "Deseja abrir a planilha?"):
                os.startfile(str(caminho))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar: {e}")

    def limpar_campos(self):
        for entry in [self.ent_visitante, self.ent_apt, self.ent_marca, self.ent_modelo, self.ent_cor, self.ent_placa]:
            entry.delete(0, 'end')

    def carregar_dados(self):
        """Carrega os dados filtrando pela data de hoje"""
        for i in self.tabela.get_children(): 
            self.tabela.delete(i)
        
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        # Otimização: Apenas lê os dados sem alterar o modo de journal
        cursor = conn.execute("SELECT * FROM veiculos_visitantes WHERE hora_entrada LIKE ? ORDER BY id DESC", (f"{data_hoje}%",))
        
        for r in cursor.fetchall():
            linha = list(r)
            for i in range(len(linha)):
                if not linha[i] or str(linha[i]).strip() == "": 
                    linha[i] = "-"
            self.tabela.insert("", "end", values=linha)
        
        conn.close()